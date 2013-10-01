from PyQt4.QtCore import QObject, QEvent, Qt, QPoint, QPointF, QRectF, QRect
from volumina.slicingtools import rect2slicing
import numpy as np
from navigationControler import NavigationInterpreter, posView2D
from volumina.layer import GrayscaleLayer


#*******************************************************************************
# T h r e s h o l d i n g  I n t e r p r e t e r                               *
#*******************************************************************************

class ThresholdingInterpreter( QObject ):
    # states
    FINAL             = 0
    DEFAULT_MODE      = 1 # normal navigation functionality
    THRESHOLDING_MODE = 2 # while pressing left mouse button allow thresholding
    NO_VALID_LAYER    = 3 # not a grayscale layer 
    
    @property
    def state( self ):
        return self._current_state

    def __init__( self, navigationControler, layerStack, posModel ):
        QObject.__init__( self )
        self._navCtrl = navigationControler
        self._navIntr = NavigationInterpreter( navigationControler )
        self._layerStack = layerStack
        self._active_layer = None
        self._active_layer_idx = -1
        self._current_state = self.FINAL
        self._current_position = QPoint(0,0)
        self._steps_mean = 10 # TODO Scale based on range
        self._steps_delta = self._steps_mean*2
        self._channel_range = dict()
        self._posModel = posModel

    def start( self ):
        if self._current_state == self.FINAL:
            self._navIntr.start()
            self._current_state = self.DEFAULT_MODE
        else:
            pass 
    
    def stop( self ):
        self._current_state = self.FINAL
        self._navIntr.stop()            
        
    def eventFilter( self, watched, event ):
        etype = event.type()
        if self._current_state == self.DEFAULT_MODE:
            if etype == QEvent.MouseButtonPress \
                    and event.button() == Qt.LeftButton \
                    and event.modifiers() == Qt.NoModifier \
                    and self._navIntr.mousePositionValid(watched, event): # TODO maybe remove, if we can find out which view is active
                print 'Left button pressed, entering thresholding mode'
                self.set_active_layer()
                if self.valid_layer:
                    self._current_state = self.THRESHOLDING_MODE
                    if self._active_layer_idx in self._channel_range:
                        self._active_layer.set_normalize(0, self._channel_range[self._active_layer_idx])
                        self._current_position = watched.mapToGlobal( event.pos() )
                        return True
                else:
                    self._current_state = self.NO_VALID_LAYER
                return self._navIntr.eventFilter( watched, event )
            elif etype == QEvent.MouseButtonPress \
                    and event.button() == Qt.RightButton \
                    and event.modifiers() == Qt.NoModifier \
                    and self._navIntr.mousePositionValid(watched, event):
                self.set_active_layer()
                if self.valid_layer:
                    self.onRightClick_resetThreshold(watched, event)
                else:
                    pass # do nothing
                return True
            else:
                return self._navIntr.eventFilter( watched, event )
        elif self._current_state == self.NO_VALID_LAYER:
            return self._navIntr.eventFilter( watched, event )
        elif self._current_state == self.THRESHOLDING_MODE:
            assert self._active_layer != None, 'Thresholding: No active layer set'
            if etype == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                self._current_state = self.DEFAULT_MODE
                print 'Left button released, leaving thresholding'
                self._active_layer = None
                self.onExit_threshold( watched, event )
                return True
            elif etype == QEvent.MouseMove and event.buttons() == Qt.LeftButton:
                self.onMouseMove_thresholding(watched, event)
                return True
            else:
                return self._navIntr.eventFilter( watched, event )
        else:
            # let the navigation interpreter handle common events
            return self._navIntr.eventFilter( watched, event )
    
    def onRightClick_resetThreshold(self, imageview, event):
        self._active_layer.set_normalize(0, (0,400)) # TODO find values

    def get_number_of_channels(self, layerStack):
        for idx, layer in enumerate(layerStack):
            if layer._name == 'Input Data':
                return self._active_layer.numberOfChannels()
        return None

    def set_active_layer(self):
        for idx, layer in enumerate(self._layerStack):
            if layer._name == 'Input Data':
                self._active_layer = layer
                self._active_layer_idx= layer._channel
                return
        self._active_layer = None

    def valid_layer(self):
        return isinstance(self._active_layer, GrayscaleLayer)

    def onExit_threshold( self, watched, event ):
        pass
        # self._current_position.setX(0)
        # self._current_position.setY(0)

    def onMouseMove_thresholding(self, imageview, event):
        # trying to get data so the actual lower and upper range can be used
        print imageview.scene()._tileProvider.tiling.boundingRectF()
        sceneRectF = imageview.viewportRect()
        x, y = sceneRectF.x(), sceneRectF.y()
        x2, y2 = x + sceneRectF.width(), y + sceneRectF.height()
        startPoint = imageview.mapScene2Data( QPoint(x,y) )
        data_x, data_y, = startPoint.x(), startPoint.y()
        stopPoint = imageview.mapScene2Data( QPoint(x2, y2) )
        data_x2, data_y2, = stopPoint.x(), stopPoint.y()
        data_x = max(data_x, 0)
        data_y = max(data_y, 0)
        shape2D = posView2D( list(self._posModel.shape5D[1:4]), axis=self._posModel.activeView )
        data_x2 = min(data_x2, shape2D[0])
        data_y2 = min(data_y2, shape2D[1])
        #tile_nos = imageview.scene()._tileProvider.tiling.intersected( sceneRectF )
        #stack_id = imageview.scene()._tileProvider._current_stack_id
#        for tile_no in tile_nos:
#            qimg, progress = imageview.scene()._tileProvider._cache.tile(stack_id, tile_no)
#            print progress
#            print qimg.format()

#        for i, v in enumerate(reversed(imageview.scene()._tileProvider._sims)):
#            visible, layerOpacity, layerImageSource = v
#            if not visible:
#                continue
#            print layerImageSource
#            patch = imageview.scene()._tileProvider._cache.layer(stack_id, layerImageSource, tile_nos[0] )
#            print 'pppppppppppp ' , patch.format()

        ##### patch = self._cache.layer(stack_id, layerImageSource, tile_nr )
        # print imageview.scene().dataRect.x()
        # print imageview.scene().dataRect.y()
        # print imageview.scene().dataRect.rect()
        # print '## ', imageview.scene()._tileProvider.tiling.scene2data.mapRect(imageview.scene().dataRect.rect())
        
#        print 'S_ID: ' , stack_id
#        print '## ', imageview.scene()._tileProvider._cache

        # print rect2slicing(QRect(0,0,229,136))
        #slicing = rect2slicing( QRect(data_x, data_y, data_x2 - data_x, data_y2 - data_y) )
        x_pos = self._posModel.slicingPos5D[1]
        y_pos = self._posModel.slicingPos5D[2]
        z_pos = self._posModel.slicingPos5D[3]
        if self._posModel.activeView == 0:
            slicing = [slice(0, 1), slice(x_pos, x_pos+1), slice(data_x, data_x2), slice(data_y, data_y2), slice(self._active_layer_idx, self._active_layer_idx+1)]
        if self._posModel.activeView == 2:
            slicing = [slice(0, 1), slice(data_x, data_x2), slice(y_pos, y_pos+1), slice(data_y, data_y2), slice(self._active_layer_idx, self._active_layer_idx+1)]
        if self._posModel.activeView == 2:
            slicing = [slice(0, 1), slice(data_x, data_x2), slice(data_y, data_y2), slice(z_pos, z_pos+1), slice(self._active_layer_idx, self._active_layer_idx+1)]
        request = self._active_layer._datasources[0].request(slicing)
        result = request.wait()
        print "RESULT INFO:", result.shape, result.min(), result.max()
        '''
        print self._active_layer._datasources[0].request(QRectF(100.,100.,
                                                                100.,100.)) 
        print self._active_layer._datasources[0]._rawSource._orig_outslot
        print imageview.scene()._tileProvider
        o = imageview.scene().data2scene.map(QPointF(imageview.oldX,
                                                     imageview.oldY))
        n = imageview.scene().data2scene.map(QPointF(imageview.x,imageview.y))
        dx = n.x()-o.x()
        dy = o.y()-n.y()
        '''

        if self._active_layer_idx not in self._channel_range:
            range_lower = self._active_layer.normalize[0][0]
            range_upper = self._active_layer.normalize[0][1]
        else:
            range = self._channel_range[self._active_layer_idx]
            print '----------' , range
            print self._channel_range
            range_lower = range[0]
            range_upper = range[1]
        # don't know what version is more efficient
        # range_delta = np.sqrt((range_upper - range_lower)**2) 
        range_delta = np.abs(range_upper - range_lower)
        range_mean = range_lower + range_delta/2.0
        print range_lower, range_upper, range_delta, range_mean
        pos = imageview.mapMouseCoordinates2Data( event.pos() )
        #pos = imageview.mapToGlobal( event.pos() )
        dx =  pos.x() - self._current_position.x()
        dy =  self._current_position.y() - pos.y()

        # print 'Difference: ' , dx, ',',dy
        if dx > 0.0:
            # move mean to right
            range_mean += self._steps_mean
        elif dx < 0.0:
            # move mean to left
            range_mean -= self._steps_mean
        
        if dy > 0.0:
            # increase delta
            range_delta += self._steps_delta
        elif dy < 0.0:
            # decrease delta
            range_delta -= self._steps_delta
        # if range_delta < 1:
          #  range_delta = 1

        print range_lower, range_upper, range_delta, range_mean

        # check the bounds, ugly use min max values actually present
        if range_mean < -4096.0:
            range_mean = -4096.0
        elif range_mean > 4096.0:
            range_mean = 4096.0
        
        if range_delta < 1:
            range_delta = 1
        elif range_delta > 2*4096.0: 
            range_delta = 2*4096.0

        a = range_mean - range_delta/2.0
        b = range_mean + range_delta/2.0

        if a < -4096.0:
            a = -4096.0
        elif a > 4096.0:
            a = 4096.0
        
        if b < -4096.0:
            b = -4096.0
        elif b > 4096.0:
            b = 4096.0

        assert a <= b 

        # TODO test if in allowed range (i.e. max and min of data)
        self._active_layer.set_normalize(0, (a,b))
        self._channel_range[self._active_layer_idx] = (a,b)
        self._current_position = pos


        '''
        p = event.pos()
        # print imageview.scene() # find out which view is active
        print self._active_layer._name , ' - ' , self._active_layer._channel
        layerIdx = 0 # default for grayscale
        self._active_layer.set_normalize(layerIdx, (-100, 100))
        print 'Thresholding', p.x(), ' - ' , p.y() 
        '''

#*******************************************************************************
# T h r e s h o l d i n g  C o n t r o l e r                                   *
#*******************************************************************************

# TODO Class not needed, remove
class ThresholdingControler(QObject):
    
    def __init__(self, positionModel):
        QObject.__init__(self, parent=None)
        self._positionModel = positionModel

