

#include<iostream>

#include"FoxTree.h"


void main()
{
	std::vector<Point3D> points;
	Point3D tempPt;

	//FILE* inFile = fopen("test.xyz", "r");
	FILE* inFile = fopen("output_tree.xyz", "r");

	if (inFile)
	{
		int r, g, b;
		while (!feof(inFile))
		{
			fscanf(inFile, "%lf %lf %lf %d %d %d\n",
				&tempPt.x, &tempPt.y, &tempPt.z, &r, &g, &b);
			points.push_back(tempPt);
		}
		fclose(inFile);
	}
	else
	{
		std::cout << "There was an error in data loading..." << std::endl;
		return; 
	} 

	//
	//Parameters
	const double Radius = 3.5; 
	const double verticalResolution = 1.0; 
	const int miniPtsPerCluster = 3;
	//Initialization
	FoxTree* foxTree = new FoxTree(points, Radius, verticalResolution, miniPtsPerCluster);

	//Topdown
	foxTree->separateTrees(1, 1);
	//Output
	foxTree->outputTrees("test-1.5-1.0-5.xyz", foxTree->m_nTrees); 
	std::cout << "Finished" << std::endl;

	if (foxTree) delete foxTree; foxTree = NULL;
}
