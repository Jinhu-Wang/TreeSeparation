/*
*	Copyright (C) 2016 by
*       Jinhu Wang (jinhu.wang@tudelft.nl)
*       Roderik Lindenbergh (r.c.lindenbergh@tudelft.nl) [http://doris.tudelft.nl/~rlindenbergh/]
*       Laser and Optical Remote Sensing
*	Dept. of Geoscience and Remote Sensing
*	TU Delft, https://tudelft.nl
*
*	This is free software; you can redistribute it and/or modify
*	it under the terms of the GNU General Public License Version 3
*	as published by the Free Software Foundation.
*
*	TreeSeparation is distributed in the hope that it will be useful,
*	but WITHOUT ANY WARRANTY; without even the implied warranty of
*	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
*	GNU General Public License for more details.
*
*	You should have received a copy of the GNU General Public License
*	along with this program. If not, see <http://www.gnu.org/licenses/>.
*/


#include"FoxTree.h"

FoxTree::FoxTree()
	: m_Points(nullptr)
	, m_nNumPts(0)
	, m_nTreeIndex(0)
	, m_nVerticalResolution(0.0)
	, m_nRadius(0.0)
	, m_nMinPtSeeds(5)
	//, m_Voxel(nullptr)
{
}

//Default constructor;
FoxTree::FoxTree(std::vector<Point3D> points, double radius, double verticalResolution, int minPtNum)
{
	this->m_nVerticalResolution = verticalResolution;
	this->m_nRadius = radius;
	this->m_nMinPtSeeds = minPtNum;
	this->m_nTreeIndex = 0;

	this->m_nNumPts = points.size();
	this->m_Points = new Point3D[points.size()];
	for (size_t i = 0; i < points.size(); ++i)
	{
		this->m_Points[i].x = points.at(i).x;
		this->m_Points[i].y = points.at(i).y;
		this->m_Points[i].z = points.at(i).z;
		this->m_Points[i].ptID = i;

		if (points.at(i).x > this->m_nBBX.xMax) this->m_nBBX.xMax = points.at(i).x;
		if (points.at(i).y > this->m_nBBX.yMax) this->m_nBBX.yMax = points.at(i).y;
		if (points.at(i).z > this->m_nBBX.zMax) this->m_nBBX.zMax = points.at(i).z;

		if (points.at(i).x < this->m_nBBX.xMin) this->m_nBBX.xMin = points.at(i).x;
		if (points.at(i).y < this->m_nBBX.yMin) this->m_nBBX.yMin = points.at(i).y;
		if (points.at(i).z < this->m_nBBX.zMin) this->m_nBBX.zMin = points.at(i).z;
	}
}


//Default descructor;
FoxTree::~FoxTree()
{
	if (m_Points) delete[] m_Points; m_Points = nullptr;
}

//Initaite the tree points and also the three parameters;
void FoxTree::initialize(std::vector<Point3D> points, double radius, double verticalResolution, int minPtsNum)
{
	if (points.empty()) return;

	this->m_nRadius = radius;
	this->m_nVerticalResolution = verticalResolution;
	this->m_nMinPtSeeds = minPtsNum;

	this->loadPoints(points);
}


//Load the points to the class;
void FoxTree::loadPoints(std::vector<Point3D> points)
{
	this->m_nNumPts = points.size();
	this->m_Points = new Point3D[points.size()];

	for (size_t i = 0; i < points.size(); ++i)
	{
		this->m_Points[i].x = points.at(i).x;
		this->m_Points[i].y = points.at(i).y;
		this->m_Points[i].z = points.at(i).z;
		this->m_Points[i].ptID = i;

		if (points.at(i).x > this->m_nBBX.xMax) this->m_nBBX.xMax = points.at(i).x;
		if (points.at(i).y > this->m_nBBX.yMax) this->m_nBBX.yMax = points.at(i).y;
		if (points.at(i).z > this->m_nBBX.zMax) this->m_nBBX.zMax = points.at(i).z;

		if (points.at(i).x < this->m_nBBX.xMin) this->m_nBBX.xMin = points.at(i).x;
		if (points.at(i).y < this->m_nBBX.yMin) this->m_nBBX.yMin = points.at(i).y;
		if (points.at(i).z < this->m_nBBX.zMin) this->m_nBBX.zMin = points.at(i).z;
	}
}


//Obtain points within the designated height interval;
std::vector<int> FoxTree::getPts(double lower, double higher)
{
	std::vector<int> ptIndices;
	ptIndices.clear();

	for (int i = 0; i < m_nNumPts; ++i)
	{
		if (this->m_Points[i].z <= higher && this->m_Points[i].z > lower)
		{
			ptIndices.push_back(this->m_Points[i].ptID);
		}
	}
	return ptIndices;
}


//Run tree separation;
void FoxTree::separateTrees()
{
	this->topDownSeparation(this->m_nRadius, this->m_nVerticalResolution);
}


//Perform tree individualization w.r.t. the given direction;
// 1 == from top downwards;
// -1 == from bottom upwards;
void FoxTree::separateTrees(int ptOrVoxel, int direction)
{
	if (ptOrVoxel == 1)
	{
		if (direction == 1)
		{
			this->topDownSeparation(this->m_nRadius, this->m_nVerticalResolution);
		}
		else if (direction == -1)
		{
			this->bottomUpSeparation(this->m_nRadius, this->m_nVerticalResolution);
		}
		else
		{
			std::cout << "Direction should be either 1(topdown) or -1(bottomup)." << std::endl;
			return;
		}
	}
	else if(ptOrVoxel == -1)
	{
	}
} 


//Tree individulization from top layer downwards;
void FoxTree::topDownSeparation(double radius, double verticalResolution)
{
	// Start top-down separation
	std::cout << "=============================================" << std::endl;
	std::cout << "Start Tree individulization from top layer downwards" << std::endl;

	bool isTopLayer = true;

	std::cout << "The height of tree is: " << this->m_nBBX.zMax << "->" << this->m_nBBX.zMin << std::endl;
	int layerNum = (this->m_nBBX.zMax - this->m_nBBX.zMin) / verticalResolution + 1;
	std::cout << "The total number of layer is: " << layerNum << std::endl;

	for (int i = 0; i < layerNum; i++)
	{
		float heightUp = this->m_nBBX.zMax - verticalResolution * i;
		if (heightUp < this->m_nBBX.zMin) break;

		float heightDown = this->m_nBBX.zMax - verticalResolution * (i + 1);
		if (heightDown < this->m_nBBX.zMin)
		{
			float heightDown = this->m_nBBX.zMin;
		}

		clock_t startTime = clock();
		std::vector<int> ptIDs = this->getPts(heightDown, heightUp);
		if (ptIDs.empty()) continue;

		std::vector<std::vector<int>> currLayerClusters;
		currLayerClusters.clear();
		std::cout << "Total number of points in this layer: " << ptIDs.size() << std::endl;

		if (isTopLayer)
		{
			currLayerClusters = this->clusterPoints(radius, ptIDs);	// layer cluster
			this->generateTreeClusters(currLayerClusters);
			this->ConcatenateToParsedPts(currLayerClusters);
			if(currLayerClusters.size() == 0)
			{
				isTopLayer = true;
			}
			else
			{
				isTopLayer = false;
			}
		}
		else
		{
			std::vector<int> restPts = ptIDs;
			int parsedPts = 0;
			std::cout << "Incrementally assign points..." << std::endl;

			std::vector<int> pointIndices = ptIDs;
			do
			{
				parsedPts = this->m_nParsedPtIds.size();
				restPts = this->assignPtsToTrees(restPts, radius);
			} while (parsedPts != this->m_nParsedPtIds.size());

			std::cout << "Finished assigning points" << std::endl;

			std::vector<std::vector<int>> currLayerClusters;
			clock_t t0 = clock();
			std::cout << "Clustering " << ptIDs.size() << " points..." << std::endl;
			currLayerClusters = this->clusterPoints(radius, restPts);
			std::cout << "Time elapsed: " << clock() - t0 << std::endl;
			std::cout << "Finished clustering points" << std::endl;
			this->generateTreeClusters(currLayerClusters);
			this->ConcatenateToParsedPts(currLayerClusters);
		}
		clock_t endTime = clock();

		std::cout << "Processing time for height: [" << heightDown << " <=> " << heightUp << "] is: " << (endTime - startTime) / 1000 << " seconds." << std::endl;
		std::cout << "Height index: " << i+1 << std::endl;
		std::cout << "=============================================" << std::endl;
	}
}



//Perform tree individualization from bottom layer upwards;
void FoxTree::bottomUpSeparation(double radius, double verticalResolution)
{
	bool isBottomLayer = true;
	int k = 0;
	for (float height = this->m_nBBX.zMin; height <= this->m_nBBX.zMax; height += verticalResolution)
	{
		clock_t startTime = clock();
		std::vector<int> ptIDs = this->getPts(height, height + verticalResolution);
		if (ptIDs.empty()) return;

		std::vector<std::vector<int>> currLayerCluster;
		currLayerCluster.clear();
		std::cout << "Total number of points in this layer: " << ptIDs.size() << std::endl;
		if (isBottomLayer)
		{
			currLayerCluster = this->clusterPoints(radius, ptIDs);
			this->generateTreeClusters(currLayerCluster);
			this->ConcatenateToParsedPts(currLayerCluster);
			if(currLayerCluster.size() == 0)
			{
				isBottomLayer = true;
			}
			else
			{
				isBottomLayer = false;
			}
		}
		else
		{
			std::vector<int> restPts = ptIDs;
			int parsedPts = 0;
			std::cout << "Incrementally assign points..." << std::endl;
			do
			{
				parsedPts = this->m_nParsedPtIds.size();
				restPts = this->assignPtsToTrees(restPts, radius);
			} while (parsedPts != this->m_nParsedPtIds.size());
			std::cout << "Finished assigning points" << std::endl;
			
			std::vector<std::vector<int>> currLayerClusters;
			clock_t t0 = clock();
			std::cout << "Clustering "<< ptIDs.size()<<" points..." << std::endl;
			currLayerClusters = this->clusterPoints(radius, restPts);
			std::cout << "Time elapsed: " << clock() - t0 << std::endl;
			std::cout << "Finished clustering points" << std::endl;
			this->generateTreeClusters(currLayerClusters);
			this->ConcatenateToParsedPts(currLayerClusters);
		}
		clock_t endTime = clock();
		
		std::cout << "Processing time for height: [" << height <<" <=> " <<height + verticalResolution << "] is: " << (endTime - startTime)/1000 <<" seconds." <<std::endl;
		std::cout << "Height index: " << k++ << std::endl;
		std::cout << "=============================================" << std::endl;
	}
}



 
//Cluster points that are within the distance of the given radius.
/* ================================================================
   info:   对当前层的点依据半径阈值进行欧式聚类，使用KDTree；
   input:  半径阈值， 该层点的索引
   output: 剧烈簇（二维数组）
==================================================================*/
std::vector<std::vector<int>> FoxTree::clusterPoints(double radius, std::vector<int> ptIndices)
{
	std::vector<std::vector<int>> Clusters;
	Clusters.clear();

	if (ptIndices.empty()) return Clusters;

	PointCloud2<double> kdPts;
	kdPts.pts.resize(ptIndices.size());
	for (size_t i = 0; i < ptIndices.size(); ++i)
	{
		kdPts.pts[i].x = this->m_Points[ptIndices.at(i)].x;
		kdPts.pts[i].y = this->m_Points[ptIndices.at(i)].y;
		kdPts.pts[i].z = this->m_Points[ptIndices.at(i)].z;
	}
	kdTree* currKDTree = new kdTree(3, kdPts, KDTreeSingleIndexAdaptorParams(10));
	currKDTree->buildIndex();
	std::vector<std::pair<size_t, double>> pairs;
	SearchParams params;
	
	for (size_t i = 0; i < ptIndices.size(); ++i)
	{
		int ptID = ptIndices.at(i);
		if (this->m_Points[ptID].isVisited) continue;

		std::vector<int> currCluster; currCluster.clear();

		std::stack<int> tempStack;
		tempStack.push(ptID);
		
		this->m_Points[ptID].isPushed = true;

		while (!tempStack.empty())
		{
			ptID = tempStack.top();
			Point3D currPt = this->m_Points[ptID];
			if (!currPt.isVisited)
			{
				currCluster.push_back(ptID);
				this->m_Points[ptID].isVisited = true;
			}
			tempStack.pop();

			double queryPt[3];
			queryPt[0] = currPt.x;
			queryPt[1] = currPt.y;
			queryPt[2] = currPt.z;

			const size_t numPairs = currKDTree->radiusSearch(&queryPt[0], radius, pairs, params);
			for (size_t j = 0; j < numPairs; ++j)
			{
				if (!this->m_Points[ptIndices.at(pairs[j].first)].isPushed)
				{
					tempStack.push(ptIndices.at(pairs[j].first));
					this->m_Points[ptIndices.at(pairs[j].first)].isPushed = true;
				}
			}
		}
		if (currCluster.size() >= this->m_nMinPtSeeds)
		{
			Clusters.push_back(currCluster);
		}
	}

	if (currKDTree) delete currKDTree; currKDTree = nullptr;

	return Clusters;
}


//Assign tree points based on the clusters and the radius.
std::vector<int> FoxTree::assignPtsToTrees(std::vector<int> newPtIDs, double radius)
{
	std::vector<int> restPtIDs;
	restPtIDs.clear();

	int numParsePts = this->m_nParsedPtIds.size();
	PointCloud2<double> kdPtsParsed;
	kdPtsParsed.pts.resize(numParsePts);

	for (int i = 0; i < numParsePts; ++i)
	{
		int id = this->m_nParsedPtIds.at(i);
		kdPtsParsed.pts[i].x = this->m_Points[id].x;
		kdPtsParsed.pts[i].y = this->m_Points[id].y;
		kdPtsParsed.pts[i].z = this->m_Points[id].z;
	}
	
	kdTree* currKDTree = new kdTree(3, kdPtsParsed, KDTreeSingleIndexAdaptorParams(10));
	currKDTree->buildIndex();
	std::vector<std::pair<size_t, double>>pairs;
	SearchParams params;
	
	for (int i = 0; i < newPtIDs.size(); ++i)
	{
		int id = newPtIDs.at(i);

		double queryPt[3];
		queryPt[0] = this->m_Points[id].x;
		queryPt[1] = this->m_Points[id].y;
		queryPt[2] = this->m_Points[id].z;

		std::vector<size_t> retIndex(1);
		std::vector<double> distSquare(1);
		currKDTree->knnSearch(&queryPt[0], 1, &retIndex[0], &distSquare[0]);
		double dist = std::sqrt(distSquare[0]);
		if (dist < radius)
		{
			int currIndex = retIndex[0];
			int currTreeIndex = this->m_Points[m_nParsedPtIds.at(currIndex)].treeID;
			this->m_Points[id].treeID = currTreeIndex;
			this->m_nTrees.find(currTreeIndex)->second.ptIDs.push_back(id);
			this->m_nParsedPtIds.push_back(id);
		}
		else
		{
			restPtIDs.push_back(id);
		}
	}

	if (currKDTree) delete currKDTree; currKDTree = nullptr;
	return restPtIDs;
}




//Generate tree clusters based on the point indices;
/* ================================================================
   info:   根据聚类的结果生成树的聚类簇
   input:  聚类簇索引(二维数组）
==================================================================*/
void FoxTree::generateTreeClusters(std::vector<std::vector<int>> ptClusters)
{
	if (ptClusters.empty()) return;

	int treeCount = ptClusters.size();

	for (size_t i = 0; i < treeCount; ++i)
	{
		TreeCluster currTree;
		currTree.ptIDs = ptClusters.at(i);

		currTree.treeID = this->m_nTreeIndex++;
		
		std::pair<int, TreeCluster> tree(currTree.treeID, currTree);
		this->m_nTrees.insert(tree);
		this->applyTreeIndexToPts(tree);
	}
} 


//Apply the tree indices from the given point clusters;
void FoxTree::applyTreeIndexToPts(std::pair<int, TreeCluster> treeClusters)
{
	int ptNumber = treeClusters.second.ptIDs.size();
	
	for (int i = 0; i < ptNumber; ++i)
	{
		int ptID = treeClusters.second.ptIDs.at(i);

		this->m_Points[ptID].treeID = treeClusters.first;
	}
}



//Concatenate the points to the parsed points in the class;
void FoxTree::ConcatenateToParsedPts(std::vector<int> ptIDs)
{
	if (ptIDs.empty()) return;

	for (size_t i = 0; i < ptIDs.size(); ++i)
	{
		this->m_nParsedPtIds.push_back(ptIDs.at(i));
	}
}



//Concatenate the points of the given clusters to the parsed trees in the class;
void FoxTree::ConcatenateToParsedPts(std::vector<std::vector<int>> clusters)
{
	if (clusters.empty()) return;

	for (int i = 0; i < clusters.size(); ++i)
	{
		for (int j = 0; j < clusters.at(i).size(); ++j)
		{
			this->m_nParsedPtIds.push_back(clusters.at(i).at(j));
		}
	}
}


//Output points w.r.t. different tree indices;
void FoxTree::outputTrees(std::string filename, std::map<int, TreeCluster> trees)
{
	FILE* file = fopen(filename.c_str(), "w");

	for (int i = 0; i < trees.size(); ++i)
	{
		int r, g, b;
		r = rand() % 255;
		g = rand() % 255;
		b = rand() % 255;

		// TODO: have bug
		for (int j = 0; j < trees.at(i).ptIDs.size(); ++j)
		{
			int id = trees.at(i).ptIDs.at(j);

			Point3D pt = this->m_Points[id];
			fprintf(file, "%d %lf %lf %lf %d %d %d\n",
				pt.treeID, pt.x, pt.y, pt.z,
				r, g, b);
		}
	}
	fclose(file);
}


//Output points w.r.t. different clusters;
void FoxTree::outputClusters(std::string filename, std::vector<std::vector<int>> ptIDs)
{
	FILE* file = fopen(filename.c_str(), "w");
	for (int i = 0; i < ptIDs.size(); ++i)
	{
		int r, g, b;
		r = rand() % 255;
		g = rand() % 255;
		b = rand() % 255;
		for(int j=0; j<ptIDs.at(i).size(); ++j)
		{
			int id = ptIDs.at(i).at(j);
			Point3D pt = this->m_Points[id];
			fprintf(file, "%lf %lf %lf %d %d %d\n",
				pt.x, pt.y, pt.z, r, g, b);
		}
	}
	fclose(file);
}

//Output points.
void FoxTree::outputPts(std::string fileName, std::vector<int> ptIDs)
{
	FILE *file = fopen(fileName.c_str(), "w");
	for (int i = 0; i < ptIDs.size(); ++i)
	{
		int r, g, b;
		r = rand() % 255;
		g = rand() % 255;
		b = rand() % 255;
		Point3D pt = this->m_Points[ptIDs.at(i)];
		fprintf(file, "%lf %lf %lf %d %d %d\n",
			pt.x, pt.y, pt.z, r, g, b);
	}
	fclose(file);
}

