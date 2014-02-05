import os
from PyQt4.QtGui import QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout
from volumina.utility import decode_to_qstring
from dvidclient.gui.contents_browser import ContentsBrowser
from lazyflow.utility import isUrl

class DvidVolumeExportOptionsWidget(QWidget):    
    def __init__(self, parent):
        super( DvidVolumeExportOptionsWidget, self ).__init__(parent)
        self._initUi()

    def _initUi(self):
        self.urlLabel = QLabel(parent=self)
        self.specifyButton = QPushButton("Specify...", parent=self, clicked=self._onSpecifyClicked)
        
        layout = QHBoxLayout()
        layout.addWidget(self.urlLabel)
        layout.addStretch()
        layout.addWidget(self.specifyButton)
        
        outerLayout = QVBoxLayout(self)
        outerLayout.addLayout(layout)
        outerLayout.addStretch()
        
        self.setLayout( outerLayout )

    def initSlot(self, filepathSlot):
        self._urlSlot = filepathSlot

    def showEvent(self, event):
        super(DvidVolumeExportOptionsWidget, self).showEvent(event)
        self.updateFromSlot()
        
    def updateFromSlot(self):
        if self._urlSlot.ready():
            # FIXME: Choose a default dvid url...            
            file_path = self._urlSlot.value
            if not isUrl( file_path ):
                file_path = ""

            # Remove extension
            file_path = os.path.splitext(file_path)[0]
            self.urlLabel.setText( decode_to_qstring(file_path) )
            
            # Re-configure the slot in case we removed the extension
            self._urlSlot.setValue( file_path )
    
    def _onSpecifyClicked(self):
        # FIXME don't hardcode hostname list
        browser = ContentsBrowser( ["localhost:8000"], mode="specify_new", parent=self )
        if browser.exec_() == ContentsBrowser.Accepted:
            hostname, dataset_index, data_name, node_uuid = browser.get_selection()

            url = "http://{hostname}/api/node/{node_uuid}/{data_name}".format( **locals() )
            self._urlSlot.setValue( url )
            self.urlLabel.setText( url )

if __name__ == "__main__":
    from PyQt4.QtGui import QApplication
    from lazyflow.graph import Graph

    from lazyflow.operators.ioOperators import OpExportDvidVolume

    op = OpExportDvidVolume(transpose_axes=True, graph=Graph())

    app = QApplication([])
    w = DvidVolumeExportOptionsWidget(None)
    w.initSlot(op.NodeDataUrl)
    w.show()
    app.exec_()

    print "New Dataset URL: {}".format( op.NodeDataUrl.value )

