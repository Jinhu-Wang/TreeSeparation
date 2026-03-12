"""
Python implementation of TreeSeparation with Parallel Processing

Original Repository: https://github.com/Jinhu-Wang/TreeSeparation

Re-implemented and Parallelized in Python.

License: GNU General Public License Version 3
"""

import glob
import multiprocessing
import os
import sys
import time
import traceback

try:
    import numpy as np
    from scipy.spatial import cKDTree
except ImportError as e:
    print("Error: Missing required libraries.")
    print(f"Details: {e}")
    print("Please run: pip install numpy scipy")
    sys.exit(1)

# =========================================================
#                   HELPER FUNCTIONS
# =========================================================

def cluster_layer_worker(layer_data):
    """
    Worker function to cluster a single layer of points.
    Executed in parallel processes.
    Returns ALL clusters found (even single points) to allow logic downstream to decide.
    """
    coords, global_idx, radius = layer_data
    
    if len(coords) == 0:
        return []

    # Build local KDTree for this layer
    tree = cKDTree(coords)
    
    # Internal BFS / Region Growing
    visited = np.zeros(len(coords), dtype=bool)
    clusters = []
    
    indices_map = {i: g_idx for i, g_idx in enumerate(global_idx)}
    
    for i in range(len(coords)):
        if visited[i]:
            continue
            
        # Start new cluster
        component = []
        stack = [i]
        visited[i] = True
        
        while stack:
            curr = stack.pop()
            component.append(indices_map[curr])
            
            # Find neighbors
            neighbors = tree.query_ball_point(coords[curr], radius)
            
            for nb in neighbors:
                if not visited[nb]:
                    visited[nb] = True
                    stack.append(nb)
        
        clusters.append(component)
        
    return clusters

# =========================================================
#                   MAIN CLASS
# =========================================================

class FoxTree:
    def __init__(self, points_array, radius, vertical_resolution, min_pts_per_cluster):
        self.radius = radius
        self.vertical_resolution = vertical_resolution
        self.min_pts_seeds = min_pts_per_cluster
        
        self.points_data = points_array
        self.num_pts = len(points_array)
        
        # tree_ids: -1 means unassigned
        self.tree_ids = np.full(self.num_pts, -1, dtype=int)
        
        # Bounding box
        self.z_min = np.min(points_array[:, 2])
        self.z_max = np.max(points_array[:, 2])
        
        # Tracking
        self.parsed_pt_indices = [] # Keep track of ALL points assigned to trees
        self.next_tree_id = 0
        self.trees = {} # Map ID -> List[indices]

    def separate_trees_parallel(self):
        """
        Orchestrates the parallel layer-wise clustering followed by sequential linking.
        """
        print(f"  [Algorithm] Starting Parallel Separation on {multiprocessing.cpu_count()} cores...")
        
        # 1. SLICING
        # --------------------------------
        t_slice_start = time.time()
        layers = []
        curr_height = self.z_max
        
        while curr_height >= self.z_min:
            lower = curr_height - self.vertical_resolution
            upper = curr_height
            
            mask = (self.points_data[:, 2] > lower) & (self.points_data[:, 2] <= upper)
            layer_indices = np.where(mask)[0]
            
            if len(layer_indices) > 0:
                layer_coords = self.points_data[layer_indices]
                layers.append((layer_coords, layer_indices, self.radius))
            
            curr_height -= self.vertical_resolution
            
        t_slice_end = time.time()
        print(f"  [Time] Slicing ({len(layers)} layers): {t_slice_end - t_slice_start:.4f} sec")

        # 2. PARALLEL CLUSTERING
        # --------------------------------
        t_cluster_start = time.time()
        
        if layers:
            with multiprocessing.Pool() as pool:
                all_layer_clusters = pool.map(cluster_layer_worker, layers)
        else:
            all_layer_clusters = []
            
        t_cluster_end = time.time()
        print(f"  [Time] Parallel Clustering: {t_cluster_end - t_cluster_start:.4f} sec")

        # 3. SEQUENTIAL LINKING (Top-Down)
        # --------------------------------
        t_link_start = time.time()
        
        for i, layer_clusters in enumerate(all_layer_clusters):
            if not layer_clusters:
                continue

            # Flatten current layer clusters
            current_layer_pts_indices = [idx for cluster in layer_clusters for idx in cluster]
            
            if not current_layer_pts_indices:
                continue

            # Map: Global Point ID -> Tree ID it connects to (if any)
            local_pt_to_tree = {}

            # If trees exist above, check for connections
            if self.parsed_pt_indices:
                parsed_coords = self.points_data[self.parsed_pt_indices]
                # NOTE: Building this tree is the bottleneck, but necessary for correctness.
                parsed_tree = cKDTree(parsed_coords)
                
                current_coords = self.points_data[current_layer_pts_indices]
                
                # Find nearest neighbor in the cloud above
                dists, neighbors = parsed_tree.query(current_coords, k=1, distance_upper_bound=self.radius)
                
                for k, dist in enumerate(dists):
                    if dist <= self.radius and dist != float('inf'):
                        parsed_global_idx = self.parsed_pt_indices[neighbors[k]]
                        tree_id = self.tree_ids[parsed_global_idx]
                        local_pt_to_tree[current_layer_pts_indices[k]] = tree_id

            # Process clusters based on connectivity
            for cluster in layer_clusters:
                # Find all unique parents this cluster touches
                parents = set()
                for pt_idx in cluster:
                    if pt_idx in local_pt_to_tree:
                        parents.add(local_pt_to_tree[pt_idx])
                
                # --- CASE 0: New Seed ---
                if len(parents) == 0:
                    if len(cluster) >= self.min_pts_seeds:
                        new_id = self.next_tree_id
                        self.next_tree_id += 1
                        self.assign_cluster_to_tree(cluster, new_id)
                
                # --- CASE 1: Simple Inheritance (One Parent) ---
                elif len(parents) == 1:
                    found_tree_id = list(parents)[0]
                    self.assign_cluster_to_tree(cluster, found_tree_id)
                    
                # --- CASE 2: Conflict / Interconnected Trees (Multiple Parents) ---
                else:
                    # The parallel clustering merged two trees. We must split them.
                    self.resolve_cluster_conflict(cluster, local_pt_to_tree)

        t_link_end = time.time()
        print(f"  [Time] Sequential Linking:  {t_link_end - t_link_start:.4f} sec")

    def resolve_cluster_conflict(self, cluster, local_pt_to_tree):
        """
        Splits a cluster that touches multiple parent trees.
        1. Assigns anchor points to their respective parents.
        2. Iteratively propagates labels into the rest of the cluster.
        3. Clusters any remaining unassigned points as new seeds.
        """
        anchors = []
        rest = []
        
        # Track points assigned *within this conflict resolution step*
        # These act as the growing front for the labels A, B, etc.
        current_assigned_indices = [] 

        # 1. Assign Anchors
        for pid in cluster:
            if pid in local_pt_to_tree:
                tid = local_pt_to_tree[pid]
                self.assign_point_to_tree(pid, tid)
                current_assigned_indices.append(pid)
            else:
                rest.append(pid)
        
        # 2. Propagate Labels (Region Growing)
        while rest:
            if not current_assigned_indices:
                break
                
            # Build tree of the current "Front"
            front_coords = self.points_data[current_assigned_indices]
            front_tree = cKDTree(front_coords)
            
            rest_coords = self.points_data[rest]
            dists, neighbors = front_tree.query(rest_coords, k=1, distance_upper_bound=self.radius)
            
            newly_assigned = []
            still_rest = []
            
            for k, dist in enumerate(dists):
                if dist <= self.radius and dist != float('inf'):
                    # Found neighbor in front
                    neighbor_idx_in_front = neighbors[k]
                    neighbor_global_idx = current_assigned_indices[neighbor_idx_in_front]
                    
                    # Inherit Tree ID
                    tid = self.tree_ids[neighbor_global_idx]
                    pid = rest[k]
                    
                    self.assign_point_to_tree(pid, tid)
                    newly_assigned.append(pid)
                else:
                    still_rest.append(rest[k])
            
            # If no progress, stop
            if not newly_assigned:
                break
                
            # Update front
            current_assigned_indices = newly_assigned
            rest = still_rest
            
        # 3. Handle Leftovers (if any parts were disconnected from anchors by radius)
        if rest:
            if len(rest) >= self.min_pts_seeds:
                new_id = self.next_tree_id
                self.next_tree_id += 1
                self.assign_cluster_to_tree(rest, new_id)

    def assign_cluster_to_tree(self, cluster_indices, t_id):
        """Batch update."""
        if t_id not in self.trees:
            self.trees[t_id] = []
        
        self.trees[t_id].extend(cluster_indices)
        self.parsed_pt_indices.extend(cluster_indices)
        self.tree_ids[cluster_indices] = t_id

    def assign_point_to_tree(self, pt_id, t_id):
        """Single point update."""
        if t_id not in self.trees:
            self.trees[t_id] = []
        
        self.trees[t_id].append(pt_id)
        self.parsed_pt_indices.append(pt_id)
        self.tree_ids[pt_id] = t_id

    def output_trees(self, filename):
        t_write_start = time.time()
        print(f"  [IO] Writing output to {os.path.basename(filename)}...")
        try:
            with open(filename, 'w') as f:
                for t_id, indices in self.trees.items():
                    r = np.random.randint(0, 255)
                    g = np.random.randint(0, 255)
                    b = np.random.randint(0, 255)
                    
                    lines = []
                    for idx in indices:
                        pt = self.points_data[idx]
                        lines.append(f"{t_id} {pt[0]:.4f} {pt[1]:.4f} {pt[2]:.4f} {r} {g} {b}\n")
                    f.writelines(lines)
            t_write_end = time.time()
            print(f"  [Time] Write Output: {t_write_end - t_write_start:.4f} sec")
        except IOError as e:
            print(f"Error writing file: {e}")

# =========================================================
#                   FILE PROCESSING
# =========================================================

def process_file(input_path, output_path, radius, v_res, min_pts):
    t_file_start = time.time()
    
    # 1. Loading
    try:
        t_load_start = time.time()
        points = np.loadtxt(input_path, usecols=(0, 1, 2))
        t_load_end = time.time()
    except Exception as e:
        print(f"Error loading {input_path}: {e}")
        return

    if points.size == 0:
        print(f"Warning: File {input_path} is empty.")
        return

    print(f"\nProcessing: {os.path.basename(input_path)} | Points: {len(points)}")
    print(f"  [Time] Data Loading: {t_load_end - t_load_start:.4f} sec")

    # 2. Separation Algorithm
    try:
        fox_tree = FoxTree(points, radius, v_res, min_pts)
        fox_tree.separate_trees_parallel()
        
        # 3. Output
        fox_tree.output_trees(output_path)
    except Exception as e:
        print(f"CRITICAL ERROR processing file: {e}")
        traceback.print_exc()
    
    t_file_end = time.time()
    print(f"  [Time] TOTAL for file: {t_file_end - t_file_start:.4f} sec")

# =========================================================
#                   MAIN ENTRY POINT
# =========================================================

if __name__ == "__main__":
    multiprocessing.freeze_support() 
    
    # --- USER PARAMETERS ---
    INPUT_DIR_NAME = "TestDatasets"
    OUTPUT_DIR_NAME = "1_Individualized_trees_parallelized"
    
    RADIUS = 1.0
    VERTICAL_RESOLUTION = 0.7
    MIN_PTS_PER_CLUSTER = 3
    
    # --- SETUP ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(script_dir, INPUT_DIR_NAME)
    output_dir = os.path.join(script_dir, OUTPUT_DIR_NAME)
    
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{INPUT_DIR_NAME}' not found.")
        sys.exit(1)
        
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    xyz_files = glob.glob(os.path.join(input_dir, "*.xyz"))
    
    if not xyz_files:
        print("No .xyz files found.")
        sys.exit(0)
        
    # --- EXECUTION ---
    print(f"Found {len(xyz_files)} files.")
    print(f"Utilizing {multiprocessing.cpu_count()} cores for parallel processing.")
    
    grand_total_start = time.time()
    
    for file_path in xyz_files:
        base_name = os.path.basename(file_path)
        name_root, ext = os.path.splitext(base_name)
        
        # Skip output files
        if f"_{RADIUS}_{VERTICAL_RESOLUTION}_{MIN_PTS_PER_CLUSTER}" in name_root:
            continue
            
        out_filename = f"{name_root}_{RADIUS}_{VERTICAL_RESOLUTION}_{MIN_PTS_PER_CLUSTER}{ext}"
        out_full_path = os.path.join(output_dir, out_filename)
        
        process_file(file_path, out_full_path, RADIUS, VERTICAL_RESOLUTION, MIN_PTS_PER_CLUSTER)
        
    print(f"\nAll tasks completed in {time.time() - grand_total_start:.2f} seconds.")
