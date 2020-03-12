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
