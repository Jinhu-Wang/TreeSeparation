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

//#include"../LasLib/include/las/lasreader.hpp"
#include <lasreader.hpp>

#include"FoxTree.h"


void main()
{
	const char *filePath = "../TestData/TsingHuaData/440882004002000103501-off-ground-1.las";

	// 读取las文件
	LASreadOpener lasReadOpener;
	lasReadOpener.set_file_name(filePath);

	LASreader *lasReader = lasReadOpener.open();
	if (!lasReader) {
		std::cout << "Can not open LAS file, Please check the file path." << std::endl;
		return;
	}

	// Get las information
	LASheader lasHeader = lasReader->header;
	unsigned int pointNum = lasHeader.number_of_point_records;

	std::cout << "LAS format: " << lasHeader.version_major << "." << lasHeader.version_minor << std::endl;
	std::cout << "The number of point: " << lasHeader.number_of_point_records << std::endl;
	std::cout << "The area of point cloud: " << lasHeader.min_x << ", " << lasHeader.min_y << " to " << lasHeader.max_x << ", " << lasHeader.max_y << std::endl;

	

	std::vector<Point3D> points;
	Point3D tempPt;
	while (lasReader->read_point())
	{
		tempPt.x = lasReader->point.get_x();
		tempPt.y = lasReader->point.get_y();
		tempPt.z = lasReader->point.get_z();
		points.push_back(tempPt);
	}



	//Reading points from ASCII formated file;
	//FILE* inFile = fopen("test-02.xyz", "r");
	//if (inFile)
	//{
	//	while (!feof(inFile))
	//	{
	//		fscanf(inFile, "%lf %lf %lf\n",
	//			&tempPt.x, &tempPt.y, &tempPt.z);
	//		points.push_back(tempPt);
	//	}
	//	fclose(inFile);
	//}
	//else
	//{
	//	std::cout << "There was an error in data loading..." << std::endl;
	//	return; 
	//} 

	
	//Parameters
	const double radius = 0.3; 
	const double verticalResolution = 0.3; 
	const int miniPtsPerCluster = 4;

	//Initialization
	FoxTree* foxTree = new FoxTree(points, radius, verticalResolution, miniPtsPerCluster);

	//Topdown direction
	foxTree->separateTrees(1, 1);

	// 测试语句
	std::cout << "成功输出。。。。" << std::endl;

	//Output separation results
	foxTree->outputTrees("../Result/440882004002000103501-off-ground-1.xyz", foxTree->m_nTrees); 
	std::cout << "Finished" << std::endl;

	if (foxTree) delete foxTree; foxTree = nullptr;
}
