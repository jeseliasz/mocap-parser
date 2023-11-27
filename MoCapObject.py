import abc
import os
import re

class MoCapObject(metaclass=abc.ABCMeta):
    # TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO
    # TODO: write about what a metaclass is and what abc is *
    # TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO
    def __init__(self, filename):
        # TODO: is it okay to put this here?
        self.text_dict = {'filename': str,
                     'frames': [],
                     'nodes': {}}

        self.file_name = filename
        self.file_content = self.getFileContent()

        self.setFileName()
        self.setMoCapDataDict()

        self.framerange = self.formatFrameRange(self.text_dict["frames"])

    def setFileName(self):
        self.text_dict["filename"] = self.file_name

    def getFileContent(self):
        return open(self.file_name).readlines()

    def setFrameRangeList(self):
        # TODO: put in logic to format the framerange as a list
        pass

    def formatFrameRange(self, frames_list):
        condensedFramerangeList = []

        currentIndex = 1
        previousIndex = 0
        startValue = frames_list[0]

        if len(frames_list) == 0:
            print('framesList is empty')
        elif len(frames_list) == 1:
            condensedFramerangeList = frames_list
        else:
            while currentIndex != len(frames_list):
                if (int(frames_list[currentIndex]) != (int(frames_list[previousIndex]) + 1)) or (
                        currentIndex == (len(frames_list) - 1)):
                    if (int(frames_list[currentIndex]) == (int(frames_list[previousIndex]) + 1)) and (
                            currentIndex == (len(frames_list) - 1)):
                        endValue = frames_list[currentIndex]
                    else:
                        endValue = frames_list[previousIndex]
                    if startValue == endValue:
                        condensedFramerangeList.append(str(endValue))
                    else:
                        appendStr = '{}-{}'.format(startValue, endValue)
                        condensedFramerangeList.append(appendStr)
                    if (int(frames_list[currentIndex]) != (int(frames_list[previousIndex]) + 1)) and (
                            currentIndex == (len(frames_list) - 1)):
                        condensedFramerangeList.append(frames_list[currentIndex])
                    startValue = frames_list[currentIndex]
                    previousIndex = currentIndex
                    currentIndex += 1
                else:
                    previousIndex = currentIndex
                    currentIndex += 1

        print("frames: {}".format(condensedFramerangeList))

        return condensedFramerangeList

    @abc.abstractmethod
    def cleanUpFile(self):
        pass

    @abc.abstractmethod
    def setMoCapDataDict(self):
        pass


class TxtObject(MoCapObject):
    def getFileContent(self):
        file_content = open(self.file_name).readlines()
        return self.cleanUpFile(file_content)

    def cleanUpFile(self, file_content):
        if file_content[0] == '\n':
            file_content = file_content[1:]
        return file_content

    def setMoCapDataDict(self):
        self.setNodes()
        frameValueList = self.setFrames()
        self.setNodeXyzFrameValues(frameValueList)

        import json
        print("* * * * * * * * * * self.text_dict: {}".format(json.dumps(self.text_dict, indent=4)))

    def setNodes(self):
        nodeline = self.file_content[0]

        if nodeline.lower().startswith('frame'):
            nodes = re.split(r'\t+', nodeline)
            allNodesDict = {}
            for node in nodes:
                uniqueNodeKey = node.split(' ')[0]
                # node's unique identifier does not yet exist in allNodesDict --> add unique identifier as key AND node as value
                if not node.lower().startswith('frame') and uniqueNodeKey not in allNodesDict:
                    xyzNodeValueDict = {node: {}}
                    allNodesDict[uniqueNodeKey] = {'enabled': True, 'xyzNodes': xyzNodeValueDict}
                # node's unique identifier already exists in allNodesDict --> update its value dictionary with new child node
                elif uniqueNodeKey in allNodesDict:
                    allNodesNestedDict = allNodesDict[uniqueNodeKey]
                    allNodesNestedDict['xyzNodes'].update({node: {}})
            self.text_dict['nodes'].update(allNodesDict)
        else:
            print(
                'Cannot parse nodes from first line in {}. Expected line must start with "frame".\nFirst line is: {}'.format(
                    os.path.basename(self.file_name), self.file_content[0]))

    def setFrames(self):
        # this may need to be placed higher up --> we also don't want this to happen if the block above did not succeed
        # TODO: what if framelines len is 0? this shouldn't really happen, but we do need to handle this
        framelines = self.file_content[1:]
        frameList = []

        testLine = framelines[0]
        testLine = testLine.strip()
        testValues = re.split(r'\t+', testLine)
        nodeNum = len(testValues[1:])

        frameValueList = []
        for i in range(nodeNum):
            frameValueList.append({})

        for line in framelines:
            # remove \n at end
            line = line.strip()
            values = re.split(r'\t+', line)
            frame = int(values[0])
            frameList.append(frame)

            for index, value in enumerate(values[1:]):
                tempRootDict = frameValueList[index]
                tempNestedDict = {'enabled': True, 'value': value}
                tempRootDict[frame] = tempNestedDict
                frameValueList[index] = tempRootDict

        self.text_dict['frames'] = frameList

        return frameValueList

    def setNodeXyzFrameValues(self, frameValueList):
        nodesDict = self.text_dict.get('nodes')
        listIndex = 0
        for nodesDictKey in nodesDict:
            nestedNodeDict = nodesDict.get(nodesDictKey)
            xyzNodesDict = nestedNodeDict['xyzNodes']
            for xyzNodesDictKey in xyzNodesDict:
                print("xyzNodesDictKey: {} ; frameValueList[listIndex]: {}".format(xyzNodesDictKey, frameValueList[listIndex]))
                xyzNodesDict[xyzNodesDictKey] = {'enabled': True, 'coords': frameValueList[listIndex]}
                listIndex += 1


class BvhObject(MoCapObject):
    def extractMoCapData(self):
        pass
