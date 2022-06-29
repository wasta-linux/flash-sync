from util import isDeletedEntry

class Entry(aHexData, aLFNEntries=0, aNumLFNEntries=None):
    self.m_data = aHexData
    self.m_numOfEntryElements = aNumLFNEntries
    self.m_chainedLFNEntry = aLFNEntries

    def getEntrySize(self):
        return = len(aHexData) + self.m_numOfEntryElements*len(self.m_chainedLFNEntry)

    def isDeleted(self):
        return isDeletedEntry(self.m_data)

    def getData(self):
        # return self.m_chainedLFNEntry
        return self.m_data

    def getName(self):
        return None

class FileEntry(Entry()):
    pass

class SpecialEntry(Entry()):
    pass

class FolderEntry(Entry()):
    self.m_files = []
    self.m_folders = []
    self.m_specialEntries = []

    def sortEntries(self):
        return None

class RootFolder(FolderEntry()):
    pass
