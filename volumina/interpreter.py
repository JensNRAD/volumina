from PyQt4.QtCore import QObject, pyqtSignal, QEvent, Qt, QPoint

class ClickReportingInterpreter(QObject):
    rightClickReceived = pyqtSignal(object, QPoint) # list of indexes, global window coordinate of click
    leftClickReceived = pyqtSignal(object, QPoint)  # ditto
    
    def __init__(self, navigationInterpreter, positionModel):
        QObject.__init__(self)
        self.baseInterpret = navigationInterpreter
        self.posModel      = positionModel

    def start( self ):
        self.baseInterpret.start()

    def stop( self ):
        self.baseInterpret.stop()

    def eventFilter( self, watched, event ):
        if event.type() == QEvent.MouseButtonPress:
            pos = [int(i) for i in self.posModel.cursorPos]
            pos = [self.posModel.time] + pos + [self.posModel.channel]

            if event.button() == Qt.LeftButton:
                gPos = watched.mapToGlobal( event.pos() )
                self.leftClickReceived.emit( pos, gPos )
            if event.button() == Qt.RightButton:
                gPos = watched.mapToGlobal( event.pos() )
                self.rightClickReceived.emit( pos, gPos )                

        # Event is always forwarded to the navigation interpreter.
        return self.baseInterpret.eventFilter(watched, event)

class ClickReportingInterpreterMRI(QObject):
    """
    Custom Class for MRI. Used for thresholding of the images while the left mouse button is pressed.
    """
    rightClickReceived = pyqtSignal(object, QPoint) # list of indexes, global window coordinate of click
    leftClickReceived = pyqtSignal(object, QPoint)  # ditto
    
    DEFAULT_MODE = 1
    THRESHOLD_MODE = 2


    def __init__(self, navigationInterpreter, positionModel, layer):
        QObject.__init__(self)
        self._baseInterpret = navigationInterpreter
        self._posModel      = positionModel
        self._layer = layer
        self._current_state = self.DEFAULT_MODE
        self._current_position = QPoint(0,0)
        self._steps_mean = 10 
        self._steps_delta = self._steps_mean

    def state( self ):
        return self._current_state

    def start( self ):
        self._baseInterpret.start()

    def stop( self ):
        self._baseInterpret.stop()
    
    def adjustThreshold( self ):
        print 'left button pressed while moving'        

    def eventFilter( self, watched, event ):
        if self._current_state == self.DEFAULT_MODE:
            if event.type() == QEvent.MouseButtonPress:
                pos = [int(i) for i in self._posModel.cursorPos]
                pos = [self._posModel.time] + pos + [self._posModel.channel]
                # print 'Position: ', watched.mapToGlobal( event.pos() )
                if event.button() == Qt.LeftButton:
                    gPos = watched.mapToGlobal( event.pos() )
                    self.leftClickReceived.emit( pos, gPos )
                    self._current_position = gPos
                    self._current_state = self.THRESHOLD_MODE
                    self.onEntry_threshold( watched, event )
                    
                if event.button() == Qt.RightButton:
                    gPos = watched.mapToGlobal( event.pos() )
                    self.rightClickReceived.emit( pos, gPos )

        elif self._current_state == self.THRESHOLD_MODE:        
            if event.type() == QEvent.MouseButtonRelease:
                self.onExit_threshold( watched, event)
                self._current_state = self.DEFAULT_MODE
                self.onEntry_default( watched, event )
            elif event.type() == QEvent.MouseMove:
                self.onMouseMove_threshold( watched, event )
                  
        # Event is always forwarded to the navigation interpreter.
        return self._baseInterpret.eventFilter(watched, event)         

    def onEntry_threshold( self, watched, event ):
        pass

    def onExit_threshold( self, watched, event ):
        self._current_position.setX(0)
        self._current_position.setY(0)
        pass

    def onMouseMove_threshold( self, watched, event ):
        '''
        TODO make faster
        TODO scale stepsize based on imagesize or some other criterion
        TODO after changing the channel the normailzation is reset to [0,255]
        '''
        range_lower = self._layer[0].normalize[0][0]
        range_upper = self._layer[0].normalize[0][1]
        range_mean = (range_lower + range_upper)/2
        range_delta = range_upper-range_mean
        # determine direction
        pos = watched.mapToGlobal( event.pos() )
        # dx = pos.x() - self._current_position[0]
        # dy = self._current_position[1] - pos.y()
        dx =  pos.x() - self._current_position.x()
        dy =  self._current_position.y() - pos.y()
        # print dx, dy
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
        
        # check the bounds
        if range_mean < 0:
            range_mean = 0
        elif range_mean > 255:
            range_mean = 255
        
        if range_delta < 1:
            range_delta = 1
        elif range_delta > 255: # 127?
            range_delta = 255
        
        # print 'Mean: ', range_mean
        # print 'delta: ' , range_delta
        tmp_a = range_mean-range_delta
        tmp_b = range_mean+range_delta
        a = tmp_a if tmp_a > 0 else 0 
        b = tmp_b if tmp_b < 255 else 255
        # print '(a,b) :', a,',',b
        self._layer[0].set_normalize(0, (a,b))
        # print '-------------'
        self._current_position = pos

    def onEntry_default( self, watched, event ):
        pass

class ClickInterpreter(QObject):
    """Intercepts mouse clicks (right clicks by default) and double
       click events on a layer and calls a given functor with the
       clicked position.

    """
       
    def __init__(self, editor, layer, onClickFunctor, parent=None, right=True, double=True):
        """ editor:         VolumeEditor object
            layer:          Layer instance on which was clicked
            onClickFunctor: a function f(layer, position5D, windowPosition)
            right: If True, intercept right clicks, otherwise intercept left clicks.
        """
        QObject.__init__(self, parent)
        self.baseInterpret = editor.navInterpret
        self.posModel      = editor.posModel
        self._onClick = onClickFunctor
        self._layer = layer
        if right:
            self.button = Qt.RightButton
        else:
            self.button = Qt.LeftButton
        self.double = double

    def start( self ):
        self.baseInterpret.start()

    def stop( self ):
        self.baseInterpret.stop()

    def eventFilter( self, watched, event ):
        etype = event.type()
        handle = False
        if etype == QEvent.MouseButtonPress and event.button() == self.button:
            handle = True
        if etype == QEvent.MouseButtonDblClick and self.double and event.button() == self.button:
            handle = True
        if handle:
            pos = self.posModel.cursorPos
            pos = [int(i) for i in pos]
            pos = [self.posModel.time] + pos + [self.posModel.channel]
            self._onClick(self._layer, tuple(pos), event.pos())
            return True
        else:
            return self.baseInterpret.eventFilter(watched, event)
