# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Copyright 2011-2014, the ilastik developers

import os
import time
import unittest as ut
from PyQt4.QtCore import QTimer
from PyQt4.QtGui import qApp, QApplication, QWidget, QHBoxLayout, QPixmap
                         
from volumina.layer import Layer
from volumina.layerstack import LayerStackModel
from volumina.widgets.layerwidget import LayerWidget

class TestLayerWidget( ut.TestCase ):
    """
    Create two layers and add them to a LayerWidget.
    Then change one of the layer visibilities and verify that the layer widget appearance updates.
    
    At the time of this writing, the widget doesn't properly repaint the selected layer (all others repaint correctly).
    """
    
    @classmethod
    def setUpClass(cls):
        if 'TRAVIS' in os.environ:
            # This test fails on Travis-CI for unknown reasons,
            #  probably due to the variability of time.sleep().
            # Skip it on Travis-CI.
            import nose
            raise nose.SkipTest

        cls.app = QApplication([])
        cls.errors = False

    @classmethod
    def tearDownClass(cls):
        del cls.app
    
    def impl(self):
        try:
            # Capture the window before we change anything
            beforeImg = QPixmap.grabWindow( self.w.winId() ).toImage()
            
            # Change the visibility of the *selected* layer
            self.o2.visible = False
            
            self.w.repaint()
            
            # Make sure the GUI is caught up on paint events
            QApplication.processEvents()
            
            # We must sleep for the screenshot to be right.
            time.sleep(0.1) 

            # Capture the window now that we've changed a layer.
            afterImg = QPixmap.grabWindow( self.w.winId() ).toImage()
    
            # Optional: Save the files so we can inspect them ourselves...
            #beforeImg.save('before.png')
            #afterImg.save('after.png')

            # Before and after should NOT match.
            assert beforeImg != afterImg
        except:
            # Catch all exceptions and print them
            # We must finish so we can quit the app.
            import traceback
            traceback.print_exc()
            TestLayerWidget.errors = True

        qApp.quit()

    def test_repaint_after_visible_change(self):
        self.model = LayerStackModel()

        self.o1 = Layer([])
        self.o1.name = "Fancy Layer"
        self.o1.opacity = 0.5
        self.model.append(self.o1)
        
        self.o2 = Layer([])
        self.o2.name = "Some other Layer"
        self.o2.opacity = 0.25
        self.model.append(self.o2)
        
        self.view = LayerWidget(None, self.model)
        self.view.show()
        self.view.updateGeometry()
    
        self.w = QWidget()
        self.lh = QHBoxLayout(self.w)
        self.lh.addWidget(self.view)
        self.w.setGeometry(100, 100, 300, 300)
        self.w.show()

        # Run the test within the GUI event loop
        QTimer.singleShot(500, self.impl )
        self.app.exec_()
        
        # Were there errors?
        assert not TestLayerWidget.errors, "There were GUI errors/failures.  See above."        
        
        
if __name__=='__main__':
    ut.main()
