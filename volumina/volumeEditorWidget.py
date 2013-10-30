#!/usr/bin/env python

#Python
from functools import partial
import copy

#SciPy
import numpy

#PyQt
from PyQt4.QtCore import Qt, QRectF, QEvent, QObject, QTimerEvent
from PyQt4.QtGui import QApplication, QWidget, QShortcut, QKeySequence, QHBoxLayout, \
                        QColor, QSizePolicy, QAction, QIcon, QSpinBox, QMenu, QDialog, QLabel, QLineEdit, QPushButton, QMainWindow

#volumina
from quadsplitter import QuadView
from sliceSelectorHud import ImageView2DHud, QuadStatusBar
from pixelpipeline.datasources import ArraySource
from volumeEditor import VolumeEditor
from volumina.utility import ShortcutManager

class __TimerEventEater( QObject ):
    def eventFilter( self, obj, ev ):
        if isinstance(obj, QSpinBox) and isinstance(ev, QTimerEvent):
            return True
        return False
_timerEater = __TimerEventEater()
        
class VolumeEditorWidget(QWidget):
    def __init__( self, parent=None, editor=None ):
        super(VolumeEditorWidget, self).__init__(parent=parent)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFocusPolicy(Qt.StrongFocus)
        
        self.editor = None
        if editor!=None:
            self.init(editor)

        self._viewMenu = None

        self.allZoomToFit = QAction(QIcon(":/icons/icons/view-fullscreen.png"), "Zoom to &Fit", self)
        self.allZoomToFit.triggered.connect(self._fitToScreen)

        self.allToggleHUD = QAction(QIcon(), "Show &HUDs", self)
        self.allToggleHUD.setCheckable(True)
        self.allToggleHUD.setChecked(True)
        self.allToggleHUD.toggled.connect(self._toggleHUDs)

        self.allCenter = QAction(QIcon(), "&Center views", self)
        self.allCenter.triggered.connect(self._centerAllImages)

        self.selectedCenter = QAction(QIcon(), "C&enter view", self)
        self.selectedCenter.triggered.connect(self._centerImage)

        self.selectedZoomToFit = QAction(QIcon(":/icons/icons/view-fullscreen.png"), "Zoom to Fit", self)
        self.selectedZoomToFit.triggered.connect(self._fitImage)

        self.selectedZoomToOriginal = QAction(QIcon(), "Reset Zoom", self)
        self.selectedZoomToOriginal.triggered.connect(self._restoreImageToOriginalSize)

        self.rubberBandZoom = QAction(QIcon(), "Rubberband Zoom", self)
        self.rubberBandZoom.triggered.connect(self._rubberBandZoom)

        self.toggleSelectedHUD = QAction(QIcon(), "Show HUD", self)
        self.toggleSelectedHUD.setCheckable(True)
        self.toggleSelectedHUD.setChecked(True)
        self.toggleSelectedHUD.toggled.connect(self._toggleSelectedHud)


    def _setupVolumeExtent( self ):
        '''Setup min/max values of position/coordinate control elements.

        Position/coordinate information is read from the volumeEditor's positionModel.

        '''
        maxTime = self.editor.posModel.shape5D[0] - 1
        self.quadview.statusBar.timeLabel.setHidden(maxTime == 0)
        self.quadview.statusBar.timeSpinBox.setHidden(maxTime == 0)
        self.quadview.statusBar.timeSpinBox.setRange(0,maxTime)
        self.quadview.statusBar.timeSpinBox.setSuffix("/{}".format( maxTime ) )
        
        for i in range(3):
            self.editor.imageViews[i].hud.setMaximum(self.editor.posModel.volumeExtent(i)-1)
    
    def init(self, volumina):
        self.editor = volumina
        
        self.hudsShown = [True]*3
        
        def onViewFocused():
            axis = self.editor._lastImageViewFocus;
            self.toggleSelectedHUD.setChecked( self.editor.imageViews[axis]._hud.isVisible() )
        self.editor.newImageView2DFocus.connect(onViewFocused)

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.setLayout(self.layout)
        
        # setup quadview
        axisLabels = ["X", "Y", "Z"]
        axisColors = [QColor("#dc143c"), QColor("green"), QColor("blue")]
        for i, v in enumerate(self.editor.imageViews):
            v.hud = ImageView2DHud(v)
            #connect interpreter
            v.hud.createImageView2DHud(axisLabels[i], 0, axisColors[i], QColor("white"))
            v.hud.sliceSelector.valueChanged.connect(partial(self.editor.navCtrl.changeSliceAbsolute, axis=i))

        self.quadview = QuadView(self, self.editor.imageViews[2],
                                 self.editor.imageViews[0], self.editor.imageViews[1],
                                 self.editor.view3d)
        self.quadview.installEventFilter(self)
        self.quadViewStatusBar = QuadStatusBar()
        self.quadViewStatusBar.createQuadViewStatusBar(
            QColor("#dc143c"),
            QColor("white"),
            QColor("green"),
            QColor("white"),
            QColor("blue"),
            QColor("white"))
        self.quadview.addStatusBar(self.quadViewStatusBar)
        self.layout.addWidget(self.quadview)

        ## Why do we have to prevent TimerEvents reaching the SpinBoxes?
        #
        # Sometimes clicking a SpinBox once caused the value to increase by
        # two. This is why:
        #
        # When a MouseClicked event is received by the SpinBox it fires a timerevent to control
        # the repeated increase of the value as long as the mouse button is pressed. The timer
        # is killed when it receives a MouseRelease event. If a slot connected to the valueChanged
        # signal of the SpinBox takes to long to process the signal the mouse release
        # and timer events get queued up and sometimes the timer event reaches the widget before
        # the mouse release event. That's why it increases the value by another step. To prevent
        # this we are blocking the timer events at the cost of no autorepeat anymore.
        #
        # See also:
        # http://lists.trolltech.com/qt-interest/2002-04/thread00137-0.html
        # http://www.qtcentre.org/threads/43078-QSpinBox-Timer-Issue
        # http://qt.gitorious.org/qt/qt/blobs/4.8/src/gui/widgets/qabstractspinbox.cpp#line1195
        self.quadview.statusBar.timeSpinBox.installEventFilter( _timerEater )

        def setTime(t):
            if t == self.editor.posModel.time:
                return
            self.editor.posModel.time = t
        self.quadview.statusBar.timeSpinBox.valueChanged.connect(setTime)
        def getTime(newT):
            self.quadview.statusBar.timeSpinBox.setValue(newT)
        self.editor.posModel.timeChanged.connect(getTime) 

        def toggleSliceIntersection(state):
            self.editor.navCtrl.indicateSliceIntersection = (state == Qt.Checked)
        self.quadview.statusBar.positionCheckBox.stateChanged.connect(toggleSliceIntersection)

        self.editor.posModel.cursorPositionChanged.connect(self._updateInfoLabels)

        def onShapeChanged():
            singletonDims = filter( lambda (i,dim): dim == 1, enumerate(self.editor.posModel.shape5D[1:4]) )
            if len(singletonDims) == 1:
                # Maximize the slicing view for this axis
                axis = singletonDims[0][0]
                self.quadview.ensureMaximized(axis)
                self.hudsShown[axis] = self.editor.imageViews[axis].hudVisible()
                self.editor.imageViews[axis].setHudVisible(False)
                self.quadViewStatusBar.showXYCoordinates()
                
                self.quadview.statusBar.positionCheckBox.setVisible(False)
            else:
                self.quadViewStatusBar.showXYZCoordinates()
                for i in range(3):
                    self.editor.imageViews[i].setHudVisible(self.hudsShown[i])
                self.quadview.statusBar.positionCheckBox.setVisible(True)
        
            self._setupVolumeExtent()

        self.editor.shapeChanged.connect(onShapeChanged)
        
        self.updateGeometry()
        self.update()
        self.quadview.update()
        
        if hasattr(self.editor.view3d, 'bUndock'):
            self.editor.view3d.bUndock.clicked.connect(partial(self.quadview.on_dock, self.quadview.dock2_ofSplitHorizontal2))

        # shortcuts
        self._initShortcuts()

    def _toggleDebugPatches(self,show):
        self.editor.showDebugPatches = show

    def _fitToScreen(self):
        shape = self.editor.posModel.shape
        for i, v in enumerate(self.editor.imageViews):
            s = list(copy.copy(shape))
            del s[i]
            v.changeViewPort(v.scene().data2scene.mapRect(QRectF(0,0,*s)))  
            
    def _fitImage(self):
        if self.editor._lastImageViewFocus is not None:
            self.editor.imageViews[self.editor._lastImageViewFocus].fitImage()
            
    def _restoreImageToOriginalSize(self):
        if self.editor._lastImageViewFocus is not None:
            self.editor.imageViews[self.editor._lastImageViewFocus].doScaleTo()
                
    def _rubberBandZoom(self):
        if self.editor._lastImageViewFocus is not None:
            if not self.editor.imageViews[self.editor._lastImageViewFocus]._isRubberBandZoom:
                self.editor.imageViews[self.editor._lastImageViewFocus]._isRubberBandZoom = True
                self.editor.imageViews[self.editor._lastImageViewFocus]._cursorBackup = self.editor.imageViews[self.editor._lastImageViewFocus].cursor()
                self.editor.imageViews[self.editor._lastImageViewFocus].setCursor(Qt.CrossCursor)
            else:
                self.editor.imageViews[self.editor._lastImageViewFocus]._isRubberBandZoom = False
                self.editor.imageViews[self.editor._lastImageViewFocus].setCursor(self.editor.imageViews[self.editor._lastImageViewFocus]._cursorBackup)
            
    
    def _toggleHUDs(self, checked):
        for v in self.editor.imageViews:
            v.setHudVisible(checked)
            
    def _toggleSelectedHud(self, checked):
        if self.editor._lastImageViewFocus is not None:
            self.editor.imageViews[self.editor._lastImageViewFocus].setHudVisible(checked)
            
    def _centerAllImages(self):
        for v in self.editor.imageViews:
            v.centerImage()
            
    def _centerImage(self):
        if self.editor._lastImageViewFocus is not None:
            self.editor.imageViews[self.editor._lastImageViewFocus].centerImage()

    def _shortcutHelper(self, keySequence, group, description, parent, function, context = None, enabled = None, widget=None):
        shortcut = QShortcut(QKeySequence(keySequence), parent, member=function, ambiguousMember=function)
        if context != None:
            shortcut.setContext(context)
        if enabled != None:
            shortcut.setEnabled(True)

        ShortcutManager().register( group, description, shortcut, widget )
        return shortcut, group, description

    def _initShortcuts(self):
        self.shortcuts = []

        # TODO: Fix this dependency on ImageView/HUD internals
        self.shortcuts.append(self._shortcutHelper("x", "Navigation", "Minimize/Maximize x-Window", self, self.quadview.switchXMinMax, Qt.ApplicationShortcut, True, widget=self.editor.imageViews[0].hud.buttons['maximize']))
        self.shortcuts.append(self._shortcutHelper("y", "Navigation", "Minimize/Maximize y-Window", self, self.quadview.switchYMinMax, Qt.ApplicationShortcut, True, widget=self.editor.imageViews[1].hud.buttons['maximize']))
        self.shortcuts.append(self._shortcutHelper("z", "Navigation", "Minimize/Maximize z-Window", self, self.quadview.switchZMinMax, Qt.ApplicationShortcut, True, widget=self.editor.imageViews[2].hud.buttons['maximize']))
        
        
        for i, v in enumerate(self.editor.imageViews):
            self.shortcuts.append(self._shortcutHelper("+", "Navigation", "Zoom in", v,  v.zoomIn, Qt.WidgetShortcut))
            self.shortcuts.append(self._shortcutHelper("-", "Navigation", "Zoom out", v, v.zoomOut, Qt.WidgetShortcut))
            
            self.shortcuts.append(self._shortcutHelper("c", "Navigation", "Center image", v,  v.centerImage, Qt.WidgetShortcut))
            self.shortcuts.append(self._shortcutHelper("h", "Navigation", "Toggle hud", v,  v.toggleHud, Qt.WidgetShortcut))
            
            # FIXME: The nextChannel/previousChannel functions don't work right now.
            #self.shortcuts.append(self._shortcutHelper("q", "Navigation", "Switch to next channel",     v, self.editor.nextChannel,     Qt.WidgetShortcut))
            #self.shortcuts.append(self._shortcutHelper("a", "Navigation", "Switch to previous channel", v, self.editor.previousChannel, Qt.WidgetShortcut))
            
            def sliceDelta(axis, delta):
                newPos = copy.copy(self.editor.posModel.slicingPos)
                newPos[axis] += delta
                newPos[axis] = max(0, newPos[axis]) 
                newPos[axis] = min(self.editor.posModel.shape[axis]-1, newPos[axis]) 
                self.editor.posModel.slicingPos = newPos

            def jumpToFirstSlice(axis):
                newPos = copy.copy(self.editor.posModel.slicingPos)
                newPos[axis] = 0
                self.editor.posModel.slicingPos = newPos
                
            def jumpToLastSlice(axis):
                newPos = copy.copy(self.editor.posModel.slicingPos)
                newPos[axis] = self.editor.posModel.shape[axis]-1
                self.editor.posModel.slicingPos = newPos
            
            # TODO: Fix this dependency on ImageView/HUD internals
            self.shortcuts.append(self._shortcutHelper("Ctrl+Up",   "Navigation", "Slice up",   v, partial(sliceDelta, i, 1),  Qt.WidgetShortcut, widget=v.hud.buttons['slice'].upLabel))
            self.shortcuts.append(self._shortcutHelper("Ctrl+Down", "Navigation", "Slice down", v, partial(sliceDelta, i, -1), Qt.WidgetShortcut, widget=v.hud.buttons['slice'].downLabel))
            
#            self.shortcuts.append(self._shortcutHelper("p", "Navigation", "Slice up (alternate shortcut)",   v, partial(sliceDelta, i, 1),  Qt.WidgetShortcut))
#            self.shortcuts.append(self._shortcutHelper("o", "Navigation", "Slice down (alternate shortcut)", v, partial(sliceDelta, i, -1), Qt.WidgetShortcut))
            
            self.shortcuts.append(self._shortcutHelper("Ctrl+Shift+Up",   "Navigation", "10 slices up",   v, partial(sliceDelta, i, 10),  Qt.WidgetShortcut))
            self.shortcuts.append(self._shortcutHelper("Ctrl+Shift+Down", "Navigation", "10 slices down", v, partial(sliceDelta, i, -10), Qt.WidgetShortcut))
            self.shortcuts.append(self._shortcutHelper("Shift+Up",   "Navigation", "Jump to first slice",   v, partial(jumpToFirstSlice, i),  Qt.WidgetShortcut))
            self.shortcuts.append(self._shortcutHelper("Shift+Down", "Navigation", "Jump to last slice", v, partial(jumpToLastSlice, i), Qt.WidgetShortcut))

            

    def _updateInfoLabels(self, pos):
        self.quadViewStatusBar.setMouseCoords(*pos)

    def eventFilter(self, watched, event):
        # If the user performs a ctrl+scroll on the splitter itself,
        # scroll all views.
        if event.type() == QEvent.Wheel and (event.modifiers() == Qt.ControlModifier):
            for view in self.editor.imageViews:
                if event.delta() > 0:
                    view.zoomIn()
                else:
                    view.zoomOut()
            return True
        return False
    
    def getViewMenu(self, debug_mode=False):
        """
        Return a QMenu with a set of actions for our editor.
        """
        if self._viewMenu is None:
            self._initViewMenu()
        for action in self._debugActions:
            action.setEnabled( debug_mode )
            action.setVisible( debug_mode )
        return self._viewMenu

    def _initViewMenu(self):
        self._viewMenu = QMenu("View", parent=self)
        self._viewMenu.setObjectName( "view_menu" )
        self._debugActions = []
        
        # This action is saved as a member so it can be triggered from tests
        self._viewMenu.actionFitToScreen = self._viewMenu.addAction( "&Zoom to &fit" )
        self._viewMenu.actionFitToScreen.triggered.connect(self._fitToScreen)

        def toggleHud():
            hide = not self.editor.imageViews[0]._hud.isVisible()
            for v in self.editor.imageViews:
                v.setHudVisible(hide)
        # This action is saved as a member so it can be triggered from tests
        self._viewMenu.actionToggleAllHuds = self._viewMenu.addAction( "Toggle huds" )
        self._viewMenu.actionToggleAllHuds.triggered.connect(toggleHud)

        def resetAllAxes():
            for s in self.editor.imageScenes:
                s.resetAxes()
        self._viewMenu.addAction( "Reset all axes" ).triggered.connect(resetAllAxes)

        def centerAllImages():
            for v in self.editor.imageViews:
                v.centerImage()
        self._viewMenu.addAction( "Center images" ).triggered.connect(centerAllImages)

        def toggleDebugPatches(show):
            self.editor.showDebugPatches = show
        actionShowTiling = self._viewMenu.addAction( "Show Tiling" )
        actionShowTiling.setCheckable(True)
        actionShowTiling.toggled.connect(toggleDebugPatches)
        qsd = QShortcut( QKeySequence("Ctrl+D"), self, member=actionShowTiling.toggle, context=Qt.WidgetShortcut )
        ShortcutManager().register("Navigation","Show tiling",qsd)
        self._debugActions.append( actionShowTiling )

        def setCacheSize( cache_size ):
            dlg = QDialog(self)
            layout = QHBoxLayout()
            layout.addWidget( QLabel("Cached Slices Per View:") )

            spinBox = QSpinBox( parent=dlg )
            spinBox.setRange( 0, 1000 )
            spinBox.setValue( self.editor.cacheSize )
            layout.addWidget( spinBox )
            okButton = QPushButton( "OK", parent=dlg )
            okButton.clicked.connect( dlg.accept )
            layout.addWidget( okButton )
            dlg.setLayout( layout )
            dlg.setModal(True)
            if dlg.exec_() == QDialog.Accepted:
                self.editor.cacheSize = spinBox.value()
        self._viewMenu.addAction( "Set layer cache size" ).triggered.connect(setCacheSize)

        '''
        #disabled for ilastik 1.0
        def enablePrefetching( enable ):
            for scene in self.editor.imageScenes:
                scene.setPrefetchingEnabled( enable )
        actionUsePrefetching = self._viewMenu.addAction( "Use prefetching" )
        actionUsePrefetching.setCheckable(True)
        actionUsePrefetching.toggled.connect(enablePrefetching)
        '''

        def blockGuiForRendering():
            for v in self.editor.imageViews:
                v.scene().joinRenderingAllTiles()
                v.repaint()
            QApplication.processEvents()
        actionBlockGui = self._viewMenu.addAction( "Block for rendering" )
        actionBlockGui.triggered.connect(blockGuiForRendering)
        qsw = QShortcut( QKeySequence("Ctrl+B"), self, member=actionBlockGui.trigger, context=Qt.WidgetShortcut )
        ShortcutManager().register( "Navigation", "Block gui for rendering", qsw )
        self._debugActions.append( actionBlockGui )

        # ------ Separator ------
        self._viewMenu.addAction("").setSeparator(True)

        # Text only
        actionOnlyForSelectedView = self._viewMenu.addAction( "Only for selected view" )
        actionOnlyForSelectedView.setIconVisibleInMenu(True)
        font = actionOnlyForSelectedView.font()
        font.setItalic(True)
        font.setBold(True)
        actionOnlyForSelectedView.setFont(font)
        def setCurrentAxisIcon():
            """Update the icon that shows the currently selected axis."""
            actionOnlyForSelectedView.setIcon(QIcon(self.editor.imageViews[self.editor._lastImageViewFocus]._hud.axisLabel.pixmap()))
        self.editor.newImageView2DFocus.connect(setCurrentAxisIcon)
        setCurrentAxisIcon()
        
        actionFitImage = self._viewMenu.addAction( "Fit image" )
        actionFitImage.triggered.connect(self._fitImage)
        qsa = QShortcut( QKeySequence("K"), self, member=actionFitImage.trigger, context=Qt.WidgetShortcut )
        ShortcutManager().register( "Navigation", "Fit image on screen", qsa)

        def toggleSelectedHud():
            self.editor.imageViews[self.editor._lastImageViewFocus].toggleHud()
        actionToggleSelectedHud = self._viewMenu.addAction( "Toggle hud" )
        actionToggleSelectedHud.triggered.connect(toggleSelectedHud)

        def resetAxes():
            self.editor.imageScenes[self.editor._lastImageViewFocus].resetAxes()
        self._viewMenu.addAction( "Reset axes" ).triggered.connect(resetAxes)

        def centerImage():
            self.editor.imageViews[self.editor._lastImageViewFocus].centerImage()
        actionCenterImage = self._viewMenu.addAction( "Center image" )
        actionCenterImage.triggered.connect(centerImage)
        qsc = QShortcut( QKeySequence("C"), self, member=actionCenterImage.trigger, context=Qt.WidgetShortcut )
        ShortcutManager().register("Navigation","Center image",qsc)

        def restoreImageToOriginalSize():
            self.editor.imageViews[self.editor._lastImageViewFocus].doScaleTo()
        actionResetZoom = self._viewMenu.addAction( "Reset zoom" )
        actionResetZoom.triggered.connect(restoreImageToOriginalSize)
        qsw = QShortcut( QKeySequence("W"), self, member=actionResetZoom.trigger, context=Qt.WidgetShortcut )
        ShortcutManager().register("Navigation","Reset zoom",qsw)        

        def updateHudActions():
            dataShape = self.editor.dataShape
            # if the image is 2D, do not show the HUD action (issue #190)
            is2D = numpy.sum(numpy.asarray(dataShape[1:4]) == 1) == 1
            actionToggleSelectedHud.setVisible(not is2D)
            self._viewMenu.actionToggleAllHuds.setVisible(not is2D)
        self.editor.shapeChanged.connect( updateHudActions )

        # FIXME: this needs bug fixing
        #def rubberBandZoom():
        #    if hasattr(self.editor, '_lastImageViewFocus'):
        #        if not self.editor.imageViews[self.editor._lastImageViewFocus]._isRubberBandZoom:
        #            self.editor.imageViews[self.editor._lastImageViewFocus]._isRubberBandZoom = True
        #            self.editor.imageViews[self.editor._lastImageViewFocus]._cursorBackup = self.editor.imageViews[self.editor._lastImageViewFocus].cursor()
        #            self.editor.imageViews[self.editor._lastImageViewFocus].setCursor(Qt.CrossCursor)
        #        else:
        #            self.editor.imageViews[self.editor._lastImageViewFocus]._isRubberBandZoom = False
        #            self.editor.imageViews[self.editor._lastImageViewFocus].setCursor(self.editor.imageViews[self.editor._lastImageViewFocus]._cursorBackup)
        #self._viewMenu.addAction( "RubberBand zoom" ).triggered.connect(rubberBandZoom)
        

                     
#*******************************************************************************
# i f   _ _ n a m e _ _   = =   " _ _ m a i n _ _ "                            *
#*******************************************************************************
if __name__ == "__main__":
    
    import sys
    from layerstack import LayerStackModel
    from volumina.layer import GrayscaleLayer
    
    array = numpy.random.rand(1,100,100,100,1)
    array *= 255
    array = array.astype('uint8')
    
    layer = GrayscaleLayer(ArraySource(array))
    app = QApplication(sys.argv)
    layerStackModel = LayerStackModel()
    layerStackModel.insert(0,layer)
    volumeEditor = VolumeEditor(layerStackModel)
    volumeEditor.dataShape = array.shape
    volumeEditorWidget = VolumeEditorWidget(editor=volumeEditor)
    volumeEditorWidget.show()
    app.exec_()   
