/*=auto=========================================================================

  Portions (c) Copyright 2018 Robarts Research Institute. All Rights Reserved.

  See COPYRIGHT.txt
  or http://www.slicer.org/copyright/copyright.txt for details.

  Program:   3D Slicer
  Module:    $RCSfile: vtkMRMLVideoCameraStorageNode.cxx,v $
  Date:      $Date: 2018/6/16 10:54:09 $
  Version:   $Revision: 1.0 $

=========================================================================auto=*/

#include "vtkMRMLVideoCameraNode.h"
#include "vtkMRMLVideoCameraStorageNode.h"
#include "vtkMRMLScene.h"

// VTK includes
#include <vtkObjectFactory.h>
#include <vtkStringArray.h>
#include <vtkVersion.h>
#include <vtksys/SystemTools.hxx>

// OpenCV includes
#include <opencv2/videoio.hpp>
#include <opencv2/core/persistence.hpp>

//----------------------------------------------------------------------------

vtkMRMLNodeNewMacro(vtkMRMLVideoCameraStorageNode);

//----------------------------------------------------------------------------
vtkMRMLVideoCameraStorageNode::vtkMRMLVideoCameraStorageNode()
{
  this->DefaultWriteFileExtension = "xml";
}

//----------------------------------------------------------------------------
vtkMRMLVideoCameraStorageNode::~vtkMRMLVideoCameraStorageNode()
{
}

//----------------------------------------------------------------------------
void vtkMRMLVideoCameraStorageNode::PrintSelf(ostream& os, vtkIndent indent)
{
  vtkMRMLStorageNode::PrintSelf(os, indent);
}

//----------------------------------------------------------------------------
bool vtkMRMLVideoCameraStorageNode::CanReadInReferenceNode(vtkMRMLNode* refNode)
{
  return refNode->IsA("vtkMRMLVideoCameraNode");
}

//----------------------------------------------------------------------------
int vtkMRMLVideoCameraStorageNode::ReadDataInternal(vtkMRMLNode* refNode)
{
  vtkMRMLVideoCameraNode* cameraNode = dynamic_cast <vtkMRMLVideoCameraNode*>(refNode);

  std::string fullName = this->GetFullNameFromFileName();
  if (fullName.empty())
  {
    vtkErrorMacro("File name not specified");
    return 0;
  }

  // check that the file exists
  if (vtksys::SystemTools::FileExists(fullName.c_str()) == false)
  {
    vtkErrorMacro("Camera file '" << fullName.c_str() << "' not found.");
    return 0;
  }

  // compute file prefix
  cv::FileStorage fs(fullName, cv::FileStorage::READ);
  if (!fs.isOpened())
  {
    vtkErrorMacro("File cannot be opened for reading.");
    return 0;
  }

  cv::Mat intrinMat;
  cv::Mat distCoeffs;
  cv::Mat markerToSensor;
  cv::Mat cameraPlaneOffset;
  cv::FileNode intrinNode = fs["IntrinsicMatrix"];
  if (intrinNode.empty())
  {
    vtkErrorMacro("Camera file does not contain IntrinsicMatrix cv::Mat.");
    intrinMat = cv::Mat::eye(3, 3, CV_64F);
  }
  else
  {
    intrinNode >> intrinMat;
  }

  cv::FileNode distCoeffsNode = fs["DistortionCoefficients"];
  if (distCoeffsNode.empty())
  {
    vtkErrorMacro("Camera file does not contain DistortionCoefficients cv::Mat.");
    distCoeffs = cv::Mat::zeros(5, 1, CV_64F);
  }
  else
  {
    distCoeffsNode >> distCoeffs;
  }

  cv::FileNode markerToSensorNode = fs["MarkerToSensor"];
  if (markerToSensorNode.empty())
  {
    vtkErrorMacro("Camera file does not contain MarkerToSensor cv::Mat.");
    markerToSensor = cv::Mat::eye(4, 4, CV_64F);
  }
  else
  {
    markerToSensorNode >> markerToSensor;
  }

  cv::FileNode cameraPlaneNode = fs["CameraPlaneOffset"];
  if (cameraPlaneNode.empty())
  {
    vtkErrorMacro("Camera file does not contain CameraPlaneOffset cv::Mat.");
    cameraPlaneOffset = cv::Mat::zeros(3, 1, CV_64F);
  }
  else
  {
    cameraPlaneNode >> cameraPlaneOffset;
  }

  if (!fs["ReprojectionError"].empty())
  {
    cameraNode->SetReprojectionError((double)fs["ReprojectionError"]);
  }

  if (!fs["RegistrationError"].empty())
  {
    cameraNode->SetRegistrationError((double)fs["RegistrationError"]);
  }

  intrinMat.convertTo(intrinMat, CV_64F);
  distCoeffs.convertTo(distCoeffs, CV_64F);
  markerToSensor.convertTo(markerToSensor, CV_64F);
  cameraPlaneOffset.convertTo(cameraPlaneOffset, CV_64F);

  vtkNew<vtkMatrix3x3> mat;
  for (int i = 0; i < 3; ++i)
  {
    for (int j = 0; j < 3; ++j)
    {
      mat->SetElement(i, j, intrinMat.at<double>(i, j));
    }
  }
  cameraNode->SetAndObserveIntrinsicMatrix(mat);

  {
    vtkNew<vtkDoubleArray> array;
    for (int i = 0; i < distCoeffs.rows; ++i)
    {
      array->InsertNextValue(distCoeffs.at<double>(i, 0));
    }
    cameraNode->SetAndObserveDistortionCoefficients(array);
  }

  vtkNew<vtkMatrix4x4> markerToImageSensor;
  for (int i = 0; i < 4; ++i)
  {
    for (int j = 0; j < 4; ++j)
    {
      markerToImageSensor->SetElement(i, j, markerToSensor.at<double>(i, j));
    }
  }
  cameraNode->SetAndObserveMarkerToImageSensorTransform(markerToImageSensor);

  {
    vtkNew<vtkDoubleArray> array;
    for (int i = 0; i < cameraPlaneOffset.rows; ++i)
    {
      array->InsertNextValue(cameraPlaneOffset.at<double>(i, 0));
    }
    cameraNode->SetAndObserveCameraPlaneOffset(array);
  }

  return 1;
}

//----------------------------------------------------------------------------
int vtkMRMLVideoCameraStorageNode::WriteDataInternal(vtkMRMLNode* refNode)
{
  vtkMRMLVideoCameraNode* videoCameraNode = vtkMRMLVideoCameraNode::SafeDownCast(refNode);

  std::string fullName = this->GetFullNameFromFileName();
  if (fullName.empty())
  {
    vtkErrorMacro("File name not specified");
    return 0;
  }

  cv::FileStorage fs(fullName, cv::FileStorage::WRITE);

  if (!fs.isOpened())
  {
    vtkErrorMacro("Cannot open " << fullName << " for writing.");
    return 0;
  }

  if (videoCameraNode->GetIntrinsicMatrix() == NULL)
  {
    vtkInfoMacro("Intrinsincs have not been determined for this camera.");
    fs << "IntrinsicMatrix" << cv::Mat::eye(3, 3, CV_64F);
  }
  else
  {
    cv::Mat intrinMat(3, 3, CV_64F);
    for (int i = 0; i < 3; ++i)
    {
      for (int j = 0; j < 3; ++j)
      {
        intrinMat.at<double>(i, j) = videoCameraNode->GetIntrinsicMatrix()->GetElement(i, j);
      }
    }
    fs << "IntrinsicMatrix" << intrinMat;
  }

  if (videoCameraNode->GetDistortionCoefficients() == NULL)
  {
    vtkInfoMacro("Distortion coefficients have not been determined for this camera.");
    fs << "DistortionCoefficients" << cv::Mat::zeros(5, 1, CV_64F);
  }
  else
  {
    cv::Mat distCoeffs(videoCameraNode->GetDistortionCoefficients()->GetSize(), 1, CV_64F);
    for (int i = 0; i < videoCameraNode->GetDistortionCoefficients()->GetSize(); ++i)
    {
      distCoeffs.at<double>(i, 0) = videoCameraNode->GetDistortionCoefficients()->GetValue(i);
    }
    fs << "DistortionCoefficients" << distCoeffs;
  }

  if (videoCameraNode->GetMarkerToImageSensorTransform() == NULL)
  {
    vtkInfoMacro("MarkerToImageSensor matrix has not been determined for this camera.");
    fs << "MarkerToSensor" << cv::Mat::eye(4, 4, CV_64F);
  }
  else
  {
    cv::Mat mat(4, 4, CV_64F);
    for (int i = 0; i < 4; ++i)
    {
      for (int j = 0; j < 4; ++j)
      {
        mat.at<double>(i, j) = videoCameraNode->GetMarkerToImageSensorTransform()->GetElement(i, j);
      }
    }
    fs << "MarkerToSensor" << mat;
  }

  if (videoCameraNode->GetCameraPlaneOffset() == NULL)
  {
    vtkInfoMacro("Camera plane offsets have not been determined for this camera.");
    fs << "CameraPlaneOffset" << cv::Mat::zeros(3, 1, CV_64F);
  }
  else
  {
    cv::Mat planeOffsets(3, 1, CV_64F);
    for (int i = 0; i < 3; ++i)
    {
      planeOffsets.at<double>(i, 0) = videoCameraNode->GetCameraPlaneOffset()->GetValue(i);
    }
    fs << "CameraPlaneOffset" << planeOffsets;
  }

  if (videoCameraNode->IsReprojectionErrorValid())
  {
    fs << "ReprojectionError" << videoCameraNode->GetReprojectionError();
  }

  if (videoCameraNode->IsRegistrationErrorValid())
  {
    fs << "RegistrationError" << videoCameraNode->GetRegistrationError();
  }

  return 1;
}

//----------------------------------------------------------------------------
void vtkMRMLVideoCameraStorageNode::InitializeSupportedReadFileTypes()
{
  this->SupportedReadFileTypes->InsertNextValue("OpenCV XML (.xml)");
}

//----------------------------------------------------------------------------
void vtkMRMLVideoCameraStorageNode::InitializeSupportedWriteFileTypes()
{
  this->SupportedWriteFileTypes->InsertNextValue("OpenCV XML (.xml)");
}

//----------------------------------------------------------------------------
vtkMRMLVideoCameraNode* vtkMRMLVideoCameraStorageNode::GetAssociatedDataNode()
{
  if (!this->GetScene())
  {
    return NULL;
  }

  std::vector<vtkMRMLNode*> nodes;
  unsigned int numberOfNodes = this->GetScene()->GetNodesByClass("vtkMRMLVideoCameraNode", nodes);
  for (unsigned int nodeIndex = 0; nodeIndex < numberOfNodes; nodeIndex++)
  {
    vtkMRMLVideoCameraNode* node = vtkMRMLVideoCameraNode::SafeDownCast(nodes[nodeIndex]);
    if (node)
    {
      const char* storageNodeID = node->GetStorageNodeID();
      if (storageNodeID && !strcmp(storageNodeID, this->ID))
      {
        return vtkMRMLVideoCameraNode::SafeDownCast(node);
      }
    }
  }

  return NULL;
}
