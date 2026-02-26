"""
Python implementation of TreeSeparation 

Original C++ Author: Jinhu Wang (jinhu.wang@tudelft.nl)
Original Repository: https://github.com/Jinhu-Wang/TreeSeparation

License: GNU General Public License Version 3
"""

import sys
import os
import glob
import numpy as np
import time
from scipy.spatial import cKDTree

class FoxTree:
    def __init__(self, points_array, radius, vertical_resolution, min_pts_per_cluster):
        """
        :param points_array: numpy array of shape (N, 3) containing x, y, z
        """
        self.radius = radius
        self.vertical_resolution = vertical_resolution
        self.min_pts_seeds = min_pts_per_cluster
        
        # Store original data
        self.points_data = points_array
        self.num_pts = len(points_array)
        
        # Initialize attributes to track state
        # tree_ids: -1 means unassigned
        self.tree_ids = np.full(self.num_pts, -1, dtype=int)
        
        # Bounding box
        self.z_min = np.min(points_array[:, 2])
        self.z_max = np.max(points_array[:, 2])
        
        # Tracking assigned points
        self.parsed_pt_indices = [] # List of indices
        self.next_tree_id = 0
        
        # Map of tree_id -> list of point indices (for final output)
        self.trees = {}

    def get_pts_in_layer(self, lower_z, higher_z):
        """
        Obtain point indices within the designated height interval.
        z > lower and z <= higher
        """
        # Note: The C++ condition is: this->m_Points[i].z <= higher && this->m_Points[i].z > lower
        condition = (self.points_data[:, 2] > lower_z) & (self.points_data[:, 2] <= higher_z)
        return np.where(condition)[0].tolist()

    def cluster_points(self, radius, pt_indices):
        """
        Cluster points that are within the distance of the given radius.
        Replicates the Custom BFS + Radius Search logic from C++.
        """
        clusters = []
        if not pt_indices:
            return clusters

        # Create a subset of points for KDTree construction
        current_points = self.points_data[pt_indices]
        
        # Map local index (0 to len-1) back to global index (pt_indices)
        local_to_global = {i: pid for i, pid in enumerate(pt_indices)}
        
        # Build KDTree for this layer
        kdtree = cKDTree(current_points)
        
        visited = set()
        pushed = set() # To keep track of what's added to stack/queue
        
        for i in range(len(pt_indices)):
            global_idx = pt_indices[i]
            
            if global_idx in visited:
                continue

            # Start a new cluster
            curr_cluster = []
            stack = [i] # Use local index for stack
            pushed.add(i)
            
            while stack:
                curr_local_idx = stack.pop()
                curr_global_idx = local_to_global[curr_local_idx]
                
                # Check visit status
                if curr_global_idx not in visited:
                    curr_cluster.append(curr_global_idx)
                    visited.add(curr_global_idx)
                
                # Query neighbors
                # query_ball_point returns indices in the `current_points` array (local indices)
                query_pt = current_points[curr_local_idx]
                neighbor_local_indices = kdtree.query_ball_point(query_pt, radius)
                
                for nb_local_idx in neighbor_local_indices:
                    # C++ logic: if (!isPushed) -> push
                    # We check if we have pushed this local index before
                    if nb_local_idx not in pushed:
                        stack.append(nb_local_idx)
                        pushed.add(nb_local_idx)

            if len(curr_cluster) >= self.min_pts_seeds:
                clusters.append(curr_cluster)
        
        return clusters

    def assign_pts_to_trees(self, new_pt_ids, radius):
        """
        Assign tree points based on nearest neighbor in already parsed points.
        Returns the list of points that were NOT assigned.
        """
        rest_pt_ids = []
        
        if not self.parsed_pt_indices:
            return new_pt_ids

        # Build KDTree from ALL previously parsed points (as per C++ logic)
        parsed_points_data = self.points_data[self.parsed_pt_indices]
        parsed_tree = cKDTree(parsed_points_data)
        
        # Query points in the current layer
        query_data = self.points_data[new_pt_ids]
        
        # k=1 for nearest neighbor
        distances, indices = parsed_tree.query(query_data, k=1)
        
        for i, dist in enumerate(distances):
            pt_id = new_pt_ids[i]
            
            if dist < radius:
                # Find the tree ID of the nearest neighbor
                nearest_parsed_idx = self.parsed_pt_indices[indices[i]]
                found_tree_id = self.tree_ids[nearest_parsed_idx]
                
                # Assign to current point
                self.tree_ids[pt_id] = found_tree_id
                
                # Update the tree cluster list
                if found_tree_id not in self.trees:
                    self.trees[found_tree_id] = []
                self.trees[found_tree_id].append(pt_id)
                
                # Mark as parsed
                self.parsed_pt_indices.append(pt_id)
            else:
                rest_pt_ids.append(pt_id)
                
        return rest_pt_ids

    def generate_tree_clusters(self, pt_clusters):
        """
        Assign new unique Tree IDs to the newly found clusters.
        """
        for cluster_indices in pt_clusters:
            # Assign new ID
            current_id = self.next_tree_id
            self.next_tree_id += 1
            
            self.trees[current_id] = []
            
            for idx in cluster_indices:
                self.tree_ids[idx] = current_id
                self.trees[current_id].append(idx)

    def concatenate_to_parsed_pts(self, clusters):
        """
        Add clustered points to the list of parsed points.
        """
        for cluster in clusters:
            self.parsed_pt_indices.extend(cluster)

    def separate_trees(self):
        """
        Top-down separation logic.
        """
        print("Starting Top-Down Separation...")
        sep_start_time = time.time()
        
        is_top_layer = True
        layer_idx = 0
        
        # Iterate from Max Z down to Min Z
        curr_height = self.z_max
        while curr_height >= self.z_min:
            t0 = time.time()
            
            # 1. Get points in this layer
            pt_ids = self.get_pts_in_layer(curr_height - self.vertical_resolution, curr_height)
            
            if not pt_ids:
                curr_height -= self.vertical_resolution
                continue
            
            print(f"Layer {layer_idx}: Height [{curr_height - self.vertical_resolution:.2f} - {curr_height:.2f}], Points: {len(pt_ids)}")
            
            curr_layer_clusters = []
            
            if is_top_layer:
                # Just cluster points
                print(f"  Clustering {len(pt_ids)} points (Top Layer)...")
                curr_layer_clusters = self.cluster_points(self.radius, pt_ids)
                self.generate_tree_clusters(curr_layer_clusters)
                self.concatenate_to_parsed_pts(curr_layer_clusters)
                
                if len(curr_layer_clusters) > 0:
                    is_top_layer = False
            else:
                # Incrementally assign points
                rest_pts = pt_ids
                print("  Incrementally assigning points...")
                
                # Iterative assignment loop (do-while in C++)
                while True:
                    prev_parsed_count = len(self.parsed_pt_indices)
                    rest_pts = self.assign_pts_to_trees(rest_pts, self.radius)
                    curr_parsed_count = len(self.parsed_pt_indices)
                    
                    if curr_parsed_count == prev_parsed_count:
                        break
                
                print("  Finished assigning points.")
                
                # Cluster the remaining points
                if rest_pts:
                    print(f"  Clustering remaining {len(rest_pts)} points...")
                    curr_layer_clusters = self.cluster_points(self.radius, rest_pts)
                    self.generate_tree_clusters(curr_layer_clusters)
                    self.concatenate_to_parsed_pts(curr_layer_clusters)
            
            t1 = time.time()
            print(f"  Layer Processing time: {t1 - t0:.3f} seconds.")
            print("=============================================")
            
            curr_height -= self.vertical_resolution
            layer_idx += 1

        sep_end_time = time.time()
        print(f"Total Separation Algorithm Time: {sep_end_time - sep_start_time:.4f} seconds.")

    def output_trees(self, filename):
        """
        Write the results to an XYZ file.
        Format: TreeID X Y Z R G B
        """
        print(f"Writing output to {filename}...")
        try:
            with open(filename, 'w') as f:
                # C++ iterates over the map of trees
                for t_id, indices in self.trees.items():
                    # Generate random color for this tree
                    r = np.random.randint(0, 255)
                    g = np.random.randint(0, 255)
                    b = np.random.randint(0, 255)
                    
                    for idx in indices:
                        pt = self.points_data[idx]
                        # Format: TreeID X Y Z R G B
                        f.write(f"{t_id} {pt[0]:.6f} {pt[1]:.6f} {pt[2]:.6f} {r} {g} {b}\n")
            print("Finished writing file.")
        except IOError as e:
            print(f"Error writing file: {e}")

def process_file(input_path, output_path, radius, v_res, min_pts):
    """
    Handles loading, processing, and saving for a single file with timing.
    """
    file_start_time = time.time()

    # 1. Load Data
    try:
        t_load_start = time.time()
        # Load XYZ data
        points = np.loadtxt(input_path, usecols=(0, 1, 2))
        t_load_end = time.time()
    except Exception as e:
        print(f"Error loading data from {input_path}: {e}")
        return

    if points.size == 0:
        print(f"Point cloud in {input_path} is empty or invalid.")
        return

    print(f"\nProcessing: {os.path.basename(input_path)}")
    print(f"Loaded {len(points)} points.")
    print(f"  [Time] Data Loading: {t_load_end - t_load_start:.4f} sec")

    # 2. Initialization & Separation
    t_process_start = time.time()
    fox_tree = FoxTree(points, radius, v_res, min_pts)
    fox_tree.separate_trees()
    t_process_end = time.time()
    
    # 3. Output
    t_write_start = time.time()
    fox_tree.output_trees(output_path)
    t_write_end = time.time()
    
    file_end_time = time.time()

    print(f"\n--- Timing Summary for {os.path.basename(input_path)} ---")
    print(f"  Data Loading:      {t_load_end - t_load_start:.4f} sec")
    print(f"  Tree Separation:   {t_process_end - t_process_start:.4f} sec")
    print(f"  Writing Output:    {t_write_end - t_write_start:.4f} sec")
    print(f"  Total File Time:   {file_end_time - file_start_time:.4f} sec")
    print("---------------------------------------------------------")

if __name__ == "__main__":
    # =========================================================
    #                    USER PARAMETERS
    # =========================================================
    
    # Directory settings
    INPUT_DIR_NAME = "0_Test_Datasets"
    OUTPUT_DIR_NAME = "1_Individualized_trees"
    
    # Algorithm parameters
    RADIUS = 1.0              # Search radius
    VERTICAL_RESOLUTION = 0.7 # Vertical slice resolution
    MIN_PTS_PER_CLUSTER = 3   # Minimum points to form a tree seed
    
    # =========================================================
    #                   MAIN EXECUTION
    # =========================================================
    
    batch_start_time = time.time()

    # 1. Setup paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(script_dir, INPUT_DIR_NAME)
    output_dir = os.path.join(script_dir, OUTPUT_DIR_NAME)
    
    # 2. Check Input Directory
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{INPUT_DIR_NAME}' not found at {input_dir}")
        sys.exit(1)
        
    # 3. Create Output Directory if it doesn't exist
    if not os.path.exists(output_dir):
        print(f"Creating output directory: {output_dir}")
        os.makedirs(output_dir)
        
    # 4. Find all .xyz files
    xyz_files = glob.glob(os.path.join(input_dir, "*.xyz"))
    
    if not xyz_files:
        print(f"No .xyz files found in {input_dir}")
        sys.exit(0)
        
    print(f"Found {len(xyz_files)} files to process.")
    
    # 5. Process loop
    for file_path in xyz_files:
        base_name = os.path.basename(file_path)
        name_root, ext = os.path.splitext(base_name)
        
        # Skip output files if they accidentally ended up in input folder
        if f"_{RADIUS}_{VERTICAL_RESOLUTION}_{MIN_PTS_PER_CLUSTER}" in name_root:
            continue

        # Construct output filename: name_radius_res_minpts.xyz
        out_filename = f"{name_root}_{RADIUS}_{VERTICAL_RESOLUTION}_{MIN_PTS_PER_CLUSTER}{ext}"
        out_full_path = os.path.join(output_dir, out_filename)
        
        process_file(file_path, out_full_path, RADIUS, VERTICAL_RESOLUTION, MIN_PTS_PER_CLUSTER)
        
    batch_end_time = time.time()
    print(f"\nAll tasks completed in {batch_end_time - batch_start_time:.4f} seconds.")
