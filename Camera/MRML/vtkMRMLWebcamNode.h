/*=auto=========================================================================

Portions (c) Copyright 2018 Robarts Research Institute. All Rights Reserved.

See COPYRIGHT.txt
or http://www.slicer.org/copyright/copyright.txt for details.

Program:   3D Slicer
Module:    $RCSfile: vtkMRMLWebcamNode.h,v $
Date:      $Date: 2018/6/16 10:54:09 $
Version:   $Revision: 1.0 $

=========================================================================auto=*/

#ifndef __vtkMRMLWebcamNode_h
#define __vtkMRMLWebcamNode_h

// MRML includes
#include "vtkSlicerCameraModuleMRMLExport.h"

// MRML includes
#include <vtkMRMLStorableNode.h>

// VTK includes
#include <vtkMatrix3x3.h>
#include <vtkDoubleArray.h>

class VTK_SLICER_CAMERA_MODULE_MRML_EXPORT vtkMRMLWebcamNode : public vtkMRMLStorableNode
{
public:
  enum
  {
    IntrinsicsModifiedEvent = 404001,
    DistortionCoefficientsModifiedEvent
  };

public:
  static vtkMRMLWebcamNode* New();
  vtkTypeMacro(vtkMRMLWebcamNode, vtkMRMLStorableNode);
  void PrintSelf(ostream& os, vtkIndent indent) VTK_OVERRIDE;

  virtual vtkMRMLNode* CreateNodeInstance() VTK_OVERRIDE;

  ///
  /// Copy the node's attributes to this object
  virtual void Copy(vtkMRMLNode* node) VTK_OVERRIDE;

  ///
  /// Get node XML tag name (like Volume, Model)
  virtual const char* GetNodeTagName() VTK_OVERRIDE {return "Webcam";};

  ///
  /// Set intrinsic matrix
  vtkGetObjectMacro(IntrinsicMatrix, vtkMatrix3x3);
  void SetAndObserveIntrinsicMatrix(vtkMatrix3x3* intrinsicMatrix);

  vtkGetObjectMacro(DistortionCoefficients, vtkDoubleArray);
  void SetAndObserveDistortionCoefficients(vtkDoubleArray* distCoeffs);

protected:
  vtkSetObjectMacro(IntrinsicMatrix, vtkMatrix3x3);
  vtkSetObjectMacro(DistortionCoefficients, vtkDoubleArray);

  unsigned long IntrinsicObserverObserverTag;
  unsigned long DistortionCoefficientsObserverTag;

  void OnIntrinsicsModified(vtkObject* caller, unsigned long event, void* data);
  void OnDistortionCoefficientsModified(vtkObject* caller, unsigned long event, void* data);

protected:
  vtkMRMLWebcamNode();
  ~vtkMRMLWebcamNode();
  vtkMRMLWebcamNode(const vtkMRMLWebcamNode&);
  void operator=(const vtkMRMLWebcamNode&);

  vtkMatrix3x3*       IntrinsicMatrix;
  vtkDoubleArray*     DistortionCoefficients;
};

#endif