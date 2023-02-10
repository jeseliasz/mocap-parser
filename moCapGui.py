#!/usr/bin/env python

import re
import sys

import numpy

from PyQt5.QtCore import QDateTime, Qt, QTimer
from PyQt5.QtGui import QTextOption
from PyQt5.QtWidgets import (QAction, QApplication, QCheckBox, QComboBox, QDateTimeEdit,
        QDial, QDialog, QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu,
        QMenuBar, QProgressBar, QPushButton, QRadioButton, QScrollArea, QScrollBar, QSizePolicy,
        QSlider, QSpinBox, QStyleFactory, QTableWidget, QTabWidget, QTextEdit,
        QVBoxLayout, QWidget)

import moCapParser

import collections


class MoCapGui(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle('MoCap Data Parser')
        self.resize(800, 800)

        centralWidget = QWidget(self)
        self.setCentralWidget(centralWidget)
        self.mainLayout = QVBoxLayout()
        centralWidget.setLayout(self.mainLayout)

        self.checkBoxList = []
        self.checkBoxMap = {}

        self.checkboxStateChangedDict = {
            'toEnable': {},
            'toDisable': {},
            'stayDisabled': {}
        }

        self.framerangeStateChangedDict = {
            'toEnable': [],
            'toDisable': [],
            'stayDisabled': []
        }
        self._createUi()

    def openFile(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Select a MoCap File: ', '',
                                                      'All Files (*);;Text Files (*.txt);;BVH Files (*.bvh)')

        if filename:
            filedata = open(filename).read()
            self.previewBox.setPlainText(filedata)
            self.parseFileData(filename)

    def parseFileData(self, filename):
        self.fileMap = moCapParser.parseFile(filename)

        framesList = self.fileMap['frames']
        self.framerange = moCapParser.getFrameRange(framesList)
        framesStr = ', '.join([str(item) for item in self.framerange])
        self.framerangeLabel.setText('Framerange (original framerange is: {}): '.format(framesStr))

        self.populateElementsGroupBox(self.fileMap['nodes'])

        self.lineEdit.setText(framesStr)

    def populateElementsGroupBox(self, nodesMap):

        for outerKey, value in nodesMap.items():
            outerKeyCheckBox = QCheckBox('{}'.format(outerKey))
            outerKeyCheckBox.setChecked(True)
            outerKeyCheckBox.stateChanged.connect(self.outerCheckBoxStateChanged)
            gridLayout = QGridLayout()
            gridLayout.addWidget(outerKeyCheckBox, 0, 0)
            separatorLine = QFrame()
            separatorLine.setFrameShape(QFrame.VLine)
            separatorLine.setFrameShadow(QFrame.Sunken)
            gridLayout.addWidget(separatorLine, 0, 1)
            nestedCheckboxList = []
            nestedKeyIndex = 2
            for nestedKey in value['xyzNodes']:
                # TODO: all X coord values in same column, all Y in same column, all Z in same column
                # meaning... if one node is missing the Y coord, we still want X and Z in the appropriate column
                nestedKeyCheckbox = QCheckBox(nestedKey)
                nestedKeyCheckbox.setChecked(True)
                nestedKeyCheckbox.setLayoutDirection(Qt.RightToLeft)
                nestedKeyCheckbox.setEnabled(False)
                nestedCheckboxList.append(nestedKeyCheckbox)
                gridLayout.addWidget(nestedKeyCheckbox, 0, nestedKeyIndex)
                nestedKeyIndex += 1
            self.checkBoxMap[outerKeyCheckBox] = nestedCheckboxList
            self.scrollBoxLayout.addLayout(gridLayout)

    def outerCheckBoxStateChanged(self):
        for key, value in self.checkBoxMap.items():
            if key.isChecked():
                for nestedCheckbox in value:
                    nestedCheckbox.setChecked(True)
                    nestedCheckbox.setEnabled(False)
            else:
                for nestedCheckbox in value:
                    nestedCheckbox.setEnabled(True)

    def updateChanges(self):
        # TODO: framerange
        if self.checkBoxMap:
            self.checkboxStateChangedDict = self.updateCheckboxStateDict(self.checkboxStateChangedDict)

            # removing unwanted/unchecked nodes from updatedFileMap
            if self.checkboxStateChangedDict['toEnable']:
                for key, valueList in self.checkboxStateChangedDict['toEnable'].items():
                    for value in valueList:
                        self.fileMap['nodes'][key]['xyzNodes'][value]['enabled'] = True
            if self.checkboxStateChangedDict['toDisable']:
                for key, valueList in self.checkboxStateChangedDict['toDisable'].items():
                    for value in valueList:
                        self.fileMap['nodes'][key]['xyzNodes'][value]['enabled'] = False

            # TODO: do we need the copy? Or is using the original okay?
            updatedFileMap = self.fileMap.copy()
            lineEditText = self.lineEdit.text()
            framerangeRegex = re.compile('^(?:[1-9]\d\d|[1-9]?\d)(?:-(?:[1-9]\d\d|[1-9]?\d))?(?:\s*,\s*(?:[1-9]\d\d|[1-9]?\d)(?:-(?:[1-9]\d\d|[1-9]?\d))?)*$')
            lineEditText = framerangeRegex.match(lineEditText)

            # parsing framerange from line edit and getting updated framerange
            if lineEditText:
                originalFramerange = updatedFileMap['frames']
                lineEditText = lineEditText.group()
                framerangeStrList = lineEditText.split(',')
                framerangeIntList = []
                removedFramesList = []
                for value in framerangeStrList:
                    value = value.strip()
                    if '-' in value:
                        splitValueList = value.split('-')
                        startInt = int(splitValueList[0])
                        endInt = int(splitValueList[-1]) + 1
                        for intVal in range(startInt, endInt):
                            if intVal in originalFramerange:
                                framerangeIntList.append(intVal)
                            else:
                                print('Frame {} not in original framerange. Skipping.'.format(intVal))
                    else:
                        if int(value) in originalFramerange:
                            framerangeIntList.append(int(value))
                        else:
                            print('Frame {} not in original framerange. Skipping.'.format(int(value)))
                removedFramesList = numpy.setdiff1d(originalFramerange, framerangeIntList)
                updatedFileMap['frames'] = framerangeIntList
            else:
                return

            self.framerangeStateChangedDict = self.updateFrameStateDict(removedFramesList, self.framerangeStateChangedDict)

            # removing unwanted frames from updatedFileMap
            if self.framerangeStateChangedDict['toEnable']:
                for parentKey in self.fileMap['nodes'].keys():
                    for xyzKey in self.fileMap['nodes'][parentKey]['xyzNodes'].keys():
                        for frame in self.framerangeStateChangedDict['toEnable']:
                            self.fileMap['nodes'][parentKey]['xyzNodes'][xyzKey]['coords'][frame]['enabled'] = True
            if self.framerangeStateChangedDict['toDisable']:
                for parentKey in self.fileMap['nodes'].keys():
                    for xyzKey in self.fileMap['nodes'][parentKey]['xyzNodes'].keys():
                        for frame in self.framerangeStateChangedDict['toDisable']:
                            self.fileMap['nodes'][parentKey]['xyzNodes'][xyzKey]['coords'][frame]['enabled'] = False

        self.formatNewFile(updatedFileMap)

    def formatNewFile(self, updatedFileMap):
        nodesUpdatedFileMap = updatedFileMap['nodes']
        lastNode = list(nodesUpdatedFileMap)[-1]
        nestedNodeUpdatedFileMap = nodesUpdatedFileMap[lastNode]
        lastNestedNode = list(nestedNodeUpdatedFileMap['xyzNodes'])[-1]

        filedata = '\nFrames\t'
        framerangeDataList = []

        for frame in updatedFileMap['frames']:
            framerangeDataList.append('{:>3}\t'.format(frame))

        nodeMap = updatedFileMap['nodes']
        for key in nodeMap.keys():
            for nestedKey, nestedValue in nodeMap[key]['xyzNodes'].items():
                if nestedValue['enabled']:
                    filedata += nestedKey
                    if nestedKey is not lastNestedNode:
                        filedata += '\t'
                    else:
                        filedata += '\n'
                    for frameKey, frameValue in nodeMap[key]['xyzNodes'][nestedKey]['coords'].items():
                        if frameValue['enabled']:
                            for index, listValue in enumerate(framerangeDataList):
                                listFrameValue = listValue.split('\t')[0]
                                listFrameValue = listFrameValue.strip()
                                if str(frameKey) == listFrameValue:
                                    listValue += frameValue['value']
                                    if nestedKey is not lastNestedNode:
                                        listValue += '\t'
                                    else:
                                        listValue += '\n'
                                    framerangeDataList[index] = listValue

        for item in framerangeDataList:
            filedata += item

        self.previewBox.setPlainText(filedata)

    def getUncheckedCheckboxes(self):
        uncheckedDict = {}

        for key, value in self.checkBoxMap.items():
            if not key.isChecked():
                uncheckedList = []
                for nestedCheckbox in value:
                    if not nestedCheckbox.isChecked():
                        uncheckedList.append(nestedCheckbox.text())
                    uncheckedDict[key.text()] = uncheckedList

        return uncheckedDict

    # TODO: this function and updateCheckboxStateDict (immediately below) rely on the same logic --> have one function for this
    def updateFrameStateDict(self, currentRemovedFramerangeList, prevFrameStateDict):
        newToEnable = []
        newToDisable = []
        newStayDisabled = []

        # handling newToDisable
        # getting value lists for key for previous stay and to disable
        prevStayDisabled = prevFrameStateDict['stayDisabled']
        prevToDisable = prevFrameStateDict['toDisable']
        # intersection with currently disabled values
        prevStayIntersectionCurrent = [item for item in prevStayDisabled if item in currentRemovedFramerangeList]
        prevToDisableIntersectionCurrent = [item for item in prevToDisable if item in currentRemovedFramerangeList]
        # new value list for newStayDisabled
        newStayDisabled = prevStayIntersectionCurrent + prevToDisableIntersectionCurrent

        # handling newToDisable
        currentDifferencePrevToDisable = [item for item in currentRemovedFramerangeList if item not in prevToDisable]
        currentDifferencePrevStayDisabled = [item for item in currentRemovedFramerangeList if item not in prevStayDisabled]
        # new value list for newToDisable
        newToDisable = [item for item in currentDifferencePrevToDisable if item in currentDifferencePrevStayDisabled]

        # handling newToEnable
        prevToDisableUnionprevStayDisabled = prevToDisable + prevStayDisabled
        # new value list for newToEnable
        newToEnable = [item for item in prevToDisableUnionprevStayDisabled if item not in currentRemovedFramerangeList]

        currentFrameStateDict = {
            'toEnable': newToEnable,
            'toDisable': newToDisable,
            'stayDisabled': newStayDisabled
        }

        return currentFrameStateDict

    # TODO: this function and updateFrameStateDict (immediately above) rely on the same logic --> have one function for this
    def updateCheckboxStateDict(self, prevCheckboxStateDict):
        currentUncheckedDict = self.getUncheckedCheckboxes()

        newToEnable = {}
        newToDisable = {}
        newStayDisabled = {}

        for currentDisabledKey, currentDisabledValueList in currentUncheckedDict.items():
            # handling newToDisable
            # getting value lists for key for previous stay and to disable
            prevStayDisabled = prevCheckboxStateDict['stayDisabled'][currentDisabledKey] if currentDisabledKey in prevCheckboxStateDict.get('stayDisabled') else []
            prevToDisable = prevCheckboxStateDict['toDisable'][currentDisabledKey] if currentDisabledKey in prevCheckboxStateDict.get('toDisable') else []
            # intersection with currently disabled values
            prevStayIntersectionCurrent = [item for item in prevStayDisabled if item in currentDisabledValueList]
            prevToDisableIntersectionCurrent = [item for item in prevToDisable if item in currentDisabledValueList]
            # new value list for newStayDisabled
            newStayDisabled[currentDisabledKey] = prevStayIntersectionCurrent + prevToDisableIntersectionCurrent

            # handling newToDisable
            currentDifferencePrevToDisable = [item for item in currentDisabledValueList if item not in prevToDisable]
            currentDifferencePrevStayDisabled = [item for item in currentDisabledValueList if item not in prevStayDisabled]
            # new value list for newToDisable
            newToDisable[currentDisabledKey] = [item for item in currentDifferencePrevToDisable if item in currentDifferencePrevStayDisabled]

            # handling newToEnable
            prevToDisableUnionprevStayDisabled = prevToDisable + prevStayDisabled
            # new value list for newToEnable
            newToEnable[currentDisabledKey] = [item for item in prevToDisableUnionprevStayDisabled if item not in currentDisabledValueList]

        currentCheckboxStateDict = {
            'toEnable': newToEnable,
            'toDisable': newToDisable,
            'stayDisabled': newStayDisabled
        }

        return currentCheckboxStateDict

    def saveFile(self):
        # TODO: what if the user changes the checkboxes or the framerange but forgets to press the update button? Make sure to force an update before saving
        # Instead of forcing an update, why not have a flag for whether or not the update was done after modifying anything in the UI?
        # this would save time and avoid an unnecessary update
        fileName = self.fileMap['filename']
        writeFile = open(fileName, 'w')
        writeData = self.previewBox.toPlainText()
        writeFile.write(writeData)
        writeFile.close()

    def saveAsFile(self):
        # TODO: what if the user changes the checkboxes or the framerange but forgets to press the update button? Make sure to force an update before saving
        # Instead of forcing an update, why not have a flag for whether or not the update was done after modifying anything in the UI?
        # this would save time and avoid an unnecessary update
        fileName, _ = QFileDialog.getSaveFileName(self, 'Save MoCap File As...',
                                                  '', 'All Files (*);;Text Files (*.txt);;BVH Files (*.bvh)')
        writeFile = open(fileName, 'w')
        writeData = self.previewBox.toPlainText()
        writeFile.write(writeData)
        writeFile.close()

        if fileName:
            print('File saved as: {}'.format(fileName))

        self.updateFileMap(fileName)

    def updateFileMap(self, fileName):
        self.fileMap['filename'] = fileName

    def about(self):
        self.previewBox.setPlainText('About clicked')

    def _createUi(self):
        self._createActions()
        self._connectActions()
        self._createMenuBar()
        self._createFramerangeWidgets()
        self._createNodesBox()
        self._createPreviewBox()
        self._createButtons()

    def _createActions(self):
        self.openAction = QAction('&Open...', self)
        self.saveAction = QAction('&Save', self)
        self.saveAsAction = QAction('&Save As...', self)

        self.aboutAction = QAction('&About', self)

    def _connectActions(self):
        self.openAction.triggered.connect(self.openFile)
        self.saveAction.triggered.connect(self.saveFile)
        self.saveAsAction.triggered.connect(self.saveAsFile)

        self.aboutAction.triggered.connect(self.about)

    def _createMenuBar(self):
        menuBar = QMenuBar(self)

        fileMenu = QMenu('&File', self)
        menuBar.addMenu(fileMenu)
        fileMenu.addAction(self.openAction)
        fileMenu.addAction(self.saveAction)
        fileMenu.addAction(self.saveAsAction)

        helpMenu = QMenu('&Help', self)
        menuBar.addMenu(helpMenu)
        helpMenu.addAction(self.aboutAction)

        self.setMenuBar(menuBar)

        # TODO: figure out how to adjust width of menubar
        self.mainLayout.addWidget(menuBar)

    def _createFramerangeWidgets(self):
        self.framerangeLabel = QLabel(self)
        self.framerangeLabel.setText('Framerange (original framerange is: N/A): ')
        self.framerangeLabel.adjustSize()

        self.lineEdit = QLineEdit(self)
        self.lineEdit.setFixedWidth(120)

        # TODO: figure out how to left align lineEdit

        framerangeLayout = QHBoxLayout()
        framerangeLayout.addWidget(self.framerangeLabel)
        framerangeLayout.addWidget(self.lineEdit)

        self.mainLayout.addLayout(framerangeLayout)

    def _createNodesBox(self):
        scrollAreaWidget = QWidget()
        self.scrollBoxLayout = QVBoxLayout(scrollAreaWidget)
        scrollAreaWidget.setLayout(self.scrollBoxLayout)

        elementsGroupBox = QScrollArea()
        elementsGroupBox.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        elementsGroupBox.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        elementsGroupBox.setWidgetResizable(True)

        elementsGroupBox.setWidget(scrollAreaWidget)

        # TODO: aaaaall those checkboxes (to figure out while putting in logic for data)
        # TODO: figure out a way to make this a percentage of the gui size (+ will need scroll)

        self.mainLayout.addWidget(elementsGroupBox)

    def _createPreviewBox(self):
        self.previewBox = QTextEdit()
        self.previewBox.setReadOnly(True)
        self.previewBox.setWordWrapMode(QTextOption.NoWrap)

        # TODO: figure out a way to make this a percentage of the gui size (+ will need scroll)

        self.mainLayout.addWidget(self.previewBox)

    def _createButtons(self):
        resetButton = QPushButton('Reset File')
        resetButton.setDefault(True)

        updateButton = QPushButton('Update Changes')
        updateButton.setDefault(True)
        updateButton.clicked.connect(self.updateChanges)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(resetButton)
        buttonLayout.addWidget(updateButton)

        # TODO: figure out how to make buttons smaller + right-aligned

        self.mainLayout.addLayout(buttonLayout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = MoCapGui()
    gui.show()
    sys.exit(app.exec_())