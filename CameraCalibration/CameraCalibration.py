import os, vtk, qt, ctk, slicer, numpy as np
import cv2
from vtk.util.numpy_support import vtk_to_numpy

from slicer.ScriptedLoadableModule import *

# CameraCalibration
class CameraCalibration(ScriptedLoadableModule):
  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "CameraCalibration" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Camera"]
    self.parent.dependencies = []
    self.parent.contributors = ["Adam Rankin (Robarts Research Institute)"]
    self.parent.helpText = """Perform camera calibration against an external tracker."""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
"""


# CameraCalibrationWidget
class CameraCalibrationWidget(ScriptedLoadableModuleWidget):
  @staticmethod
  def get(widget, objectName):
    if widget.objectName == objectName:
      return widget
    else:
      for w in widget.children():
        resulting_widget = CameraCalibrationWidget.get(w, objectName)
        if resulting_widget:
          return resulting_widget
      return None

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)

    self.logic = CameraCalibrationLogic()

    self.isManualCapturing = False

    self.centerFiducialSelectionNode = None
    self.copyNode = None
    self.widget = None

    self.inputsContainer = None
    self.trackerContainer = None
    self.intrinsicsContainer = None
    self.autoSettingsContainer = None

    # Tracker
    self.manualButton = None
    self.semiAutoButton = None
    self.imageSelector = None
    self.cameraSelector = None
    self.cameraTransformSelector = None
    self.volumeModeButton = None
    self.cameraModeButton = None
    self.cameraContainerWidget = None
    self.volumeContainerWidget = None
    self.manualModeButton = None
    self.autoModeButton = None
    self.semiAutoModeButton = None

    # Intrinsics
    self.capIntrinsicButton = None
    self.intrinsicCheckerboardButton = None
    self.intrinsicCircleGridButton = None
    self.adaptiveThresholdButton = None
    self.normalizeImageButton = None
    self.filterQuadsButton = None
    self.fastCheckButton = None
    self.symmetricButton = None
    self.asymmetricButton = None
    self.clusteringButton = None

    # OpenCV vars
    self.objPattern = None

    self.sceneObserverTag = None

  def setup(self):
    # TODO Debug only, remove once finished
    slicer.camMod = self

    ScriptedLoadableModuleWidget.setup(self)

    # Load the UI From file
    scriptedModulesPath = eval('slicer.modules.%s.path' % self.moduleName.lower())
    scriptedModulesPath = os.path.dirname(scriptedModulesPath)
    path = os.path.join(scriptedModulesPath, 'Resources', 'UI', 'q' + self.moduleName + 'Widget.ui')
    self.widget = slicer.util.loadUI(path)
    self.layout.addWidget(self.widget)

    # Tracker calibration members
    self.inputsContainer = CameraCalibrationWidget.get(self.widget, "collapsibleButton_Inputs")
    self.trackerContainer = CameraCalibrationWidget.get(self.widget, "collapsibleButton_Tracker")
    self.intrinsicsContainer = CameraCalibrationWidget.get(self.widget, "collapsibleButton_Intrinsics")
    self.manualButton = CameraCalibrationWidget.get(self.widget, "pushButton_Manual")
    self.semiAutoButton = CameraCalibrationWidget.get(self.widget, "pushButton_SemiAuto")
    self.autoButton = CameraCalibrationWidget.get(self.widget, "pushButton_Automatic")
    self.imageSelector = CameraCalibrationWidget.get(self.widget, "comboBox_ImageSelector")
    self.cameraSelector = CameraCalibrationWidget.get(self.widget, "comboBox_CameraSource")
    self.cameraTransformSelector = CameraCalibrationWidget.get(self.widget, "comboBox_CameraTransform")
    self.volumeModeButton = CameraCalibrationWidget.get(self.widget, "radioButton_VolumeNode")
    self.cameraModeButton = CameraCalibrationWidget.get(self.widget, "radioButton_CameraMode")
    self.cameraContainerWidget = CameraCalibrationWidget.get(self.widget, "widget_CameraInput")
    self.volumeContainerWidget = CameraCalibrationWidget.get(self.widget, "widget_VolumeInput")
    self.manualModeButton = CameraCalibrationWidget.get(self.widget, "radioButton_Manual")
    self.semiAutoModeButton = CameraCalibrationWidget.get(self.widget, "radioButton_SemiAuto")
    self.autoModeButton = CameraCalibrationWidget.get(self.widget, "radioButton_Automatic")
    self.autoSettingsContainer = CameraCalibrationWidget.get(self.widget, "groupBox_AutoSettings")

    # Intrinsic calibration members
    self.capIntrinsicButton = CameraCalibrationWidget.get(self.widget, "pushButton_CaptureIntrinsic")
    self.intrinsicCheckerboardButton = CameraCalibrationWidget.get(self.widget, "radioButton_IntrinsicCheckerboard")
    self.intrinsicCircleGridButton = CameraCalibrationWidget.get(self.widget, "radioButton_IntrinsicCircleGrid")
    self.columnsSpinBox = CameraCalibrationWidget.get(self.widget, "spinBox_Columns")
    self.rowsSpinBox = CameraCalibrationWidget.get(self.widget, "spinBox_Rows")
    self.adaptiveThresholdButton = CameraCalibrationWidget.get(self.widget, "checkBox_AdaptiveThreshold")
    self.normalizeImageButton = CameraCalibrationWidget.get(self.widget, "checkBox_NormalizeImage")
    self.filterQuadsButton = CameraCalibrationWidget.get(self.widget, "checkBox_FilterQuads")
    self.fastCheckButton = CameraCalibrationWidget.get(self.widget, "checkBox_FastCheck")
    self.symmetricButton = CameraCalibrationWidget.get(self.widget, "radioButton_SymmetricGrid")
    self.asymmetricButton = CameraCalibrationWidget.get(self.widget, "radioButton_AsymmetricGrid")
    self.clusteringButton = CameraCalibrationWidget.get(self.widget, "radioButton_Clustering")

    # Hide the camera source as default is volume source
    self.cameraContainerWidget.setVisible(False)

    # Disable capture as image processing isn't active yet
    self.trackerContainer.setEnabled(False)
    self.intrinsicsContainer.setEnabled(False)

    # UI file method does not do mrml scene connections, do them manually
    self.imageSelector.setMRMLScene(slicer.mrmlScene)
    self.cameraSelector.setMRMLScene(slicer.mrmlScene)
    self.cameraTransformSelector.setMRMLScene(slicer.mrmlScene)

    # Connections
    self.capIntrinsicButton.connect('clicked(bool)', self.onIntrinsicCapture)
    self.intrinsicCheckerboardButton.connect('clicked(bool)', self.onIntrinsicModeChanged)
    self.intrinsicCircleGridButton.connect('clicked(bool)', self.onIntrinsicModeChanged)
    self.rowsSpinBox.connect('valueChanged(int)', self.onPatternChanged)
    self.columnsSpinBox.connect('valueChanged(int)', self.onPatternChanged)

    self.manualButton.connect('clicked(bool)', self.onManualButton)
    self.semiAutoButton.connect('clicked(bool)', self.onSemiAutoButton)
    self.autoButton.connect('clicked(bool)', self.onAutoButton)
    self.imageSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onImageSelected)
    self.cameraTransformSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onCameraSelected)
    self.cameraSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.volumeModeButton.connect('clicked(bool)', self.onInputModeChanged)
    self.cameraModeButton.connect('clicked(bool)', self.onInputModeChanged)
    self.manualModeButton.connect('clicked(bool)', self.onProcessingModeChanged)
    self.autoModeButton.connect('clicked(bool)', self.onProcessingModeChanged)

    self.adaptiveThresholdButton.connect('clicked(bool)', self.onFlagChanged)
    self.normalizeImageButton.connect('clicked(bool)', self.onFlagChanged)
    self.filterQuadsButton.connect('clicked(bool)', self.onFlagChanged)
    self.fastCheckButton.connect('clicked(bool)', self.onFlagChanged)
    self.symmetricButton.connect('clicked(bool)', self.onFlagChanged)
    self.asymmetricButton.connect('clicked(bool)', self.onFlagChanged)
    self.clusteringButton.connect('clicked(bool)', self.onFlagChanged)

    # Adding an observer to scene to listen for mrml node
    self.sceneObserverTag = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent, self.onNodeAdded)

    # Choose red slice only
    lm = slicer.app.layoutManager()
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)

    # Initialize pattern, etc..
    self.calculateObjectPattern()

    # Refresh Apply button state
    self.onSelect()

  def cleanup(self):
    self.capIntrinsicButton.disconnect('clicked(bool)', self.onIntrinsicCapture)
    self.intrinsicCheckerboardButton.disconnect('clicked(bool)', self.onIntrinsicModeChanged)
    self.intrinsicCircleGridButton.disconnect('clicked(bool)', self.onIntrinsicModeChanged)
    self.rowsSpinBox.disconnect('valueChanged(int)', self.onPatternChanged)
    self.columnsSpinBox.disconnect('valueChanged(int)', self.onPatternChanged)

    self.manualButton.disconnect('clicked(bool)', self.onManualButton)
    self.semiAutoButton.disconnect('clicked(bool)', self.onSemiAutoButton)
    self.autoButton.disconnect('clicked(bool)', self.onAutoButton)
    self.imageSelector.disconnect("currentNodeChanged(vtkMRMLNode*)", self.onImageSelected)
    self.cameraTransformSelector.disconnect("currentNodeChanged(vtkMRMLNode*)", self.onCameraSelected)
    self.cameraSelector.disconnect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.volumeModeButton.disconnect('clicked(bool)', self.onInputModeChanged)
    self.cameraModeButton.disconnect('clicked(bool)', self.onInputModeChanged)
    self.manualModeButton.disconnect('clicked(bool)', self.onProcessingModeChanged)
    self.autoModeButton.disconnect('clicked(bool)', self.onProcessingModeChanged)

    self.adaptiveThresholdButton.disconnect('clicked(bool)', self.onFlagChanged)
    self.normalizeImageButton.disconnect('clicked(bool)', self.onFlagChanged)
    self.filterQuadsButton.disconnect('clicked(bool)', self.onFlagChanged)
    self.fastCheckButton.disconnect('clicked(bool)', self.onFlagChanged)
    self.symmetricButton.disconnect('clicked(bool)', self.onFlagChanged)
    self.asymmetricButton.disconnect('clicked(bool)', self.onFlagChanged)
    self.clusteringButton.disconnect('clicked(bool)', self.onFlagChanged)

    slicer.mrmlScene.RemoveObserver(self.sceneObserverTag)

  def onIntrinsicCapture(self):
    vtk_im = self.imageSelector.currentNode().GetImageData()
    rows, cols, _ = vtk_im.GetDimensions()
    sc = vtk_im.GetPointData().GetScalars()
    im = vtk_to_numpy(sc)
    im = im.reshape(rows, cols, -1)

    if self.intrinsicCheckerboardButton.checked:
      self.logic.findCheckerboard(im)
    else:
      self.logic.findCircleGrid(im)

  def onImageSelected(self):
    # Set red slice to the copy node
    slicer.app.layoutManager().sliceWidget('Red').sliceLogic().GetSliceCompositeNode().SetForegroundVolumeID(self.imageSelector.currentNode().GetID())
    self.onSelect()

  def onFlagChanged(self):
    flags = 0
    if self.adaptiveThresholdButton.checked:
      flags = flags + cv2.CALIB_CB_ADAPTIVE_THRESH
    if self.normalizeImageButton.checked:
      flags = flags + cv2.CALIB_CB_NORMALIZE_IMAGE
    if self.filterQuadsButton.checked:
      flags = flags + cv2.CALIB_CB_FILTER_QUADS
    if self.fastCheckButton.checked:
      flags = flags + cv2.CALIB_CB_FAST_CHECK

    if self.symmetricButton.checked:
      flags = flags + cv2.CALIB_CB_SYMMETRIC_GRID
    if self.asymmetricButton.checked:
      flags = flags + cv2.CALIB_CB_ASYMMETRIC_GRID
    if self.clusteringButton.checked:
      flags = flags + cv2.CALIB_CB_CLUSTERING

    self.logic.setFlags(flags)

  def onCameraSelected(self):
    self.onSelect()

  def onPatternChanged(self, value):
    self.logic.calculateObjectPattern(self.rowsSpinBox.value, self.columnsSpinBox.value)

  def onIntrinsicModeChanged(self):
    if self.intrinsicCheckerboardButton.checked:
      self.adaptiveThresholdButton.enabled = True
      self.normalizeImageButton.enabled = True
      self.filterQuadsButton.enabled = True
      self.fastCheckButton.enabled = True
      self.symmetricButton.enabled = False
      self.asymmetricButton.enabled = False
      self.clusteringButton.enabled = False
    else:
      self.adaptiveThresholdButton.enabled = False
      self.normalizeImageButton.enabled = False
      self.filterQuadsButton.enabled = False
      self.fastCheckButton.enabled = False
      self.symmetricButton.enabled = True
      self.asymmetricButton.enabled = True
      self.clusteringButton.enabled = True

  def onSelect(self):
    self.capIntrinsicButton.enabled = (self.imageSelector.currentNode() or self.cameraSelector.currentNode()) and self.cameraTransformSelector.currentNode()
    self.manualButton.enabled = (self.imageSelector.currentNode() or self.cameraSelector.currentNode()) and self.cameraTransformSelector.currentNode()
    self.semiAutoButton.enabled = (self.imageSelector.currentNode() or self.cameraSelector.currentNode()) and self.cameraTransformSelector.currentNode()
    self.trackerContainer.enabled = (self.imageSelector.currentNode() or self.cameraSelector.currentNode()) and self.cameraTransformSelector.currentNode()
    self.intrinsicsContainer.enabled = (self.imageSelector.currentNode() or self.cameraSelector.currentNode()) and self.cameraTransformSelector.currentNode()

  def onInputModeChanged(self):
    if self.volumeModeButton.checked:
      self.cameraContainerWidget.setVisible(False)
      self.volumeContainerWidget.setVisible(True)
    else:
      self.cameraContainerWidget.setVisible(True)
      self.volumeContainerWidget.setVisible(False)

  def onProcessingModeChanged(self):
    if self.manualModeButton.checked:
      self.manualButton.setVisible(True)
      self.semiAutoButton.setVisible(False)
      self.autoSettingsContainer.setEnabled(False)
    elif self.semiAutoModeButton.checked:
      self.manualButton.setVisible(False)
      self.semiAutoButton.setVisible(True)
      self.autoSettingsContainer.setEnabled(True)
    else:
      self.manualButton.setVisible(True)
      self.semiAutoButton.setVisible(True)
      self.autoSettingsContainer.setEnabled(True)

  def onManualButton(self):
    if self.isManualCapturing:
      # Cancel button hit
      slicer.modules.markups.logic().StopPlaceMode()
      self.inputsContainer.setEnabled(True)
      self.trackerContainer.setEnabled(True)
      slicer.app.layoutManager().sliceWidget('Red').sliceLogic().GetSliceCompositeNode().SetForegroundVolumeID(self.centerFiducialSelectionNode.GetID())
      self.manualButton.setText('Capture')
      return()

    # Make a copy of the volume node (aka freeze cv capture) to allow user to play with detection parameters or click on center
    if self.copyNode is not None:
      # Clean up old copy
      slicer.mrmlScene.RemoveNode(self.copyNode)
      self.copyNode = None

    self.centerFiducialSelectionNode = slicer.mrmlScene.GetNodeByID(slicer.app.layoutManager().sliceWidget('Red').sliceLogic().GetSliceCompositeNode().GetForegroundVolumeID())
    self.copyNode = slicer.mrmlScene.CopyNode(self.centerFiducialSelectionNode)

    # Set red slice to the copy node
    slicer.app.layoutManager().sliceWidget('Red').sliceLogic().GetSliceCompositeNode().SetForegroundVolumeID(self.copyNode.GetID())

    # Initiate fiducial selection
    slicer.modules.markups.logic().StartPlaceMode(False)

    # Disable input changing while capture is active
    self.inputsContainer.setEnabled(False)
    self.trackerContainer.setEnabled(False)

    self.isManualCapturing = True
    self.manualButton.setText('Cancel')

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onNodeAdded(self, caller, event, callData):
    if type(callData) is slicer.vtkMRMLMarkupsFiducialNode:
      arr = [0,0,0]
      callData.GetMarkupPoint(callData.GetNumberOfMarkups()-1, 0, arr)
      callData.RemoveAllMarkups()
      slicer.mrmlScene.RemoveNode(callData)

      # Re-enable
      self.inputsContainer.setEnabled(True)
      self.trackerContainer.setEnabled(True)

      # TODO : store point and line pair

      # Resume playback
      slicer.app.layoutManager().sliceWidget('Red').sliceLogic().GetSliceCompositeNode().SetForegroundVolumeID(self.centerFiducialSelectionNode.GetID())

  def onSemiAutoButton(self):
    pass

  def onAutoButton(self):
    pass

# CameraCalibrationLogic
class CameraCalibrationLogic(ScriptedLoadableModuleLogic):
  def __init__(self):
    self.intrinsicObjectPoints = []
    self.intrinsicImagePoints = []

    self.flags = None
    self.imageSize = (0,0)
    self.objPatternRows = 0
    self.objPatternColumns = 0
    self.subPixRadius = 11
    self.objPattern = None
    self.terminationCriteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

  def setTerminationCriteria(self, criteria):
    self.terminationCriteria = criteria

  def calculateObjectPattern(self, rows, columns):
    self.objPatternRows = rows
    self.objPatternColumns = columns
    self.objPattern = np.zeros((rows * columns, 3), np.float32)
    self.objPattern[:, :2] = np.mgrid[0:columns, 0:rows].T.reshape(-1, 2)

  def setSubPixRadius(self, radius):
    self.subPixRadius = radius

  def resetIntrinsic(self):
    self.intrinsicImagePoints = []
    self.intrinsicImagePoints = []

  def setFlags(self, flags):
    self.flags = flags

  def findCheckerboard(self, image):
    self.imageSize = image.shape[::-1]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Find the chess board corners
    ret, corners = cv2.findChessboardCorners(gray, (self.objPatternRows, self.objPatternColumns), None)

    # If found, add object points, image points (after refining them)
    if ret == True:
      self.intrinsicObjectPoints.append(self.objPattern)
      self.intrinsicImagePoints.append(cv2.cornerSubPix(gray, corners, (self.subPixRadius, self.subPixRadius), (-1, -1), self.terminationCriteria))

  def findCircleGrid(self, image):
    self.imageSize = image.shape[::-1]
    ret, centers = cv2.findCirclesGrid(image, (self.objPatternRows, self.objPatternColumns), )

  def calculateIntrinsics(self):
    if len(self.intrinsicImagePoints) > 0:
      ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(self.intrinsicObjectPoints, self.intrinsicImagePoints, self.imageSize, None, None)

# CameraCalibrationTest
class CameraCalibrationTest(ScriptedLoadableModuleTest):
  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough. """
    slicer.mrmlScene.Clear(0)

  def test_CameraCalibration1(self):
    self.delayDisplay("Starting the test")
    self.delayDisplay('Test passed!')

  def runTest(self):
    """ Run as few or as many tests as needed here. """
    self.setUp()
    self.test_CameraCalibration1()