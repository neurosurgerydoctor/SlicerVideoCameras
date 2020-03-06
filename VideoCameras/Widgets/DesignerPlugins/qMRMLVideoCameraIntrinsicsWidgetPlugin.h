/*=auto=========================================================================

Portions (c) Copyright 2018 Robarts Research Institute. All Rights Reserved.

See COPYRIGHT.txt
or http://www.slicer.org/copyright/copyright.txt for details.

Program:   3D Slicer
Module:    $RCSfile: qMRMLVideoCameraIntrinsicsWidgetPlugin.h,v $
Date:      $Date: 2018/6/16 10:54:09 $
Version:   $Revision: 1.0 $

=========================================================================auto=*/

#ifndef __qMRMLVideoCameraIntrinsicsWidgetPlugin_h
#define __qMRMLVideoCameraIntrinsicsWidgetPlugin_h

#include "qSlicerVideoCamerasModuleWidgetsAbstractPlugin.h"

class Q_SLICER_MODULE_VIDEOCAMERAS_WIDGETS_PLUGINS_EXPORT
  qMRMLVideoCameraIntrinsicsWidgetPlugin
  : public QObject, public qSlicerVideoCamerasModuleWidgetsAbstractPlugin
{
  Q_OBJECT

public:
  qMRMLVideoCameraIntrinsicsWidgetPlugin(QObject* _parent = 0);

  QWidget* createWidget(QWidget* _parent);
  QString domXml() const;
  QString includeFile() const;
  bool isContainer() const;
  QString name() const;

};

#endif
