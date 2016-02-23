# Developed by Dushyant
# Known limitations: works only on selected read nodes 
# Github repo dushyantk/vfxPlumber/ (https://github.com/dushyantk/vfxPlumber/blob/master/python/utils/nuke/graphUtils.py) can be used to walk up the graph and condition @ line 229 can be skipped

from __future__ import with_statement

import os
import re
import nuke
import nukescripts

# Creating a python panel to assist the process
class WatermarkUtilityPanel( nukescripts.PythonPanel ):
    def __init__( self ):
        nukescripts.PythonPanel.__init__( self, 'Watermark Utility', 'dushyant.info.WatermarkUtility')
 
        # CREATE PANEL KNOBS
        self.nodesChoice = nuke.Enumeration_Knob( 'nodes', 'Source Nodes', ['selected', 'all'])
        self.optChoice = nuke.Enumeration_Knob( 'opt_knob', 'Watermark type', ['text', 'image'])
        self.STRING_Knob = nuke.String_Knob('text', 'text')
        self.FILE_Knob = nuke.File_Knob('file', 'watermark file')
        self.Divider_Knob = nuke.Text_Knob("divName","","")
        self.Divider_Knob2 = nuke.Text_Knob("divName2","","")
        self.FILE_Knob2 = nuke.File_Knob('out_file', 'Output path')
        self.FILE_Knob2.setTooltip('If this field is left blank, output path will be filled with source Read node\'s path with a directory named watermark on the same level, else this path will be used as the ROOT path for all outputs.')

        self.run = nuke.PyScript_Knob('run', 'Run')
        # ADD PANEL KNOBS
        self.addKnob( self.nodesChoice )
        self.addKnob( self.optChoice )
        self.addKnob( self.STRING_Knob )
        self.addKnob( self.FILE_Knob )
        self.addKnob( self.Divider_Knob )
        self.addKnob( self.FILE_Knob2 )

        self.addKnob( self.Divider_Knob2 )

        self.addKnob( self.run )

        self.FILE_Knob.setEnabled(False)

    def __doStuf( self ):
        # LAUNCH MAIN PROCEDURE
        srcNodes = { 'all': nuke.allNodes(), 'selected': nuke.selectedNodes() }
        self.w_type = self.optChoice.value()
        self.w_text = self.STRING_Knob.value() or "None"
        self.w_file = self.FILE_Knob.value() or "None"
        self.w_path = self.FILE_Knob2.value() or "None"
        if self.w_type == 'text' and self.w_text == 'None':
            nuke.message('no watermark text found, exiting here')
            return 1
        if self.w_type == 'image' and self.w_file == 'None':
            nuke.message('no watermark image found, exiting here')
            return 1
        elif self.w_type == 'image' and not os.path.isfile(self.w_file):
            nuke.message('no watermark image found, exiting here')
            return 1

        if self.w_path == 'None':
            if nuke.ask('If "Output path" field is left blank, output path will be filled with source Read node\'s path with a directory named watermark on the same level, else this path will be used as the ROOT path for all outputs.\n\n '):
                print 'All good, continuing...'
            else:
                return 1
        elif not os.path.isdir(self.w_path):
            nuke.message('the output path specified doesn\'t exists, exiting now')
            return 1
        
        self.matches = watermark_main( srcNodes[self.nodesChoice.value()], self.w_type, self.w_text, self.w_file, self.w_path )

    def knobChanged( self, knob ):
        # PERFORM CHECKS
        if knob is self.run:
            self.w_type = self.optChoice.value()
            self.__doStuf()
        elif knob is self.optChoice:
            if self.optChoice.value() == 'text':
                self.FILE_Knob.setEnabled(False)
                self.STRING_Knob.setEnabled(True)
            elif self.optChoice.value() == 'image':
                self.FILE_Knob.setEnabled(True)
                self.STRING_Knob.setEnabled(False)

# Code to add the Menu
def addPanel():
    return WatermarkUtilityPanel().addToPane()
 
menu = nuke.menu('Pane')
menu.addCommand('Watermark Utility', addPanel )
nukescripts.registerPanel( 'dushyant.info.WatermarkUtility', addPanel )

# Handy function to create directories for given write node/ can/should be use as pre-render callback 
# But currently is in use while creating the watermark node
def createWriteDirs(in_node):

    baseDir = os.path.dirname( nuke.filename(in_node) )
    viewTokenRE = re.compile( r'%V' )
    if viewTokenRE.search( baseDir ):
        nodeViews = nuke.thisNode()['views'].value().split()
        outDirs = [nuke.filenameFilter(viewTokenRE.sub(v, baseDir)) for v in nodeViews]
    else:
        outDirs = [nuke.filenameFilter(baseDir)]
    for outDir in outDirs:
        if not os.path.exists(outDir):
            print 'Creating output directory: %s' % outDir
            try:
                os.makedirs(outDir)
            except (OSError, IOError), e:
                import errno
                if e.errno != errno.EEXIST:
                    raise

# Handy Procedure to de-select everything if and when required
def deselect():
    if nuke.selectedNodes():
        for i in nuke.selectedNodes():
            i['selected'].setValue(False)

# The hero procedure of the code
def watermark_proc(in_node, w_type, w_text, w_file, w_path):

    in_node_name = in_node['name'].getValue()

    with nuke.Root():
        watermark = nuke.createNode('dushyant_info_watermark_node')

        print watermark
        is_text = False
        if w_type == 'text':
            is_text = True
        elif w_type == 'image':
            is_text = False
        print is_text
        watermark.setName( "%s_Watermark" % in_node_name )


        #Setting knobs
        # calling nodes from the Gizmo
        w_read = nuke.toNode( '%s.watermark_image' % watermark.name() )
        w_write = nuke.toNode( '%s.Write' % watermark.name() )
        print w_write
        # Processing write node paths

        read_file = in_node['file'].getValue()
        basename = os.path.basename(read_file)
        if w_path == 'None':
            write_file = '%s/watermark/%s' % ( os.path.dirname(read_file), basename )

        else:
            write_file = os.path.join( w_path, os.path.splitext(basename)[0].split('.')[0], basename )

        w_write['file'].fromScript(write_file)

        createWriteDirs(w_write)

        # Setting Input/Output

        # Adding root I/O

        watermark.setInput(0, in_node)

        # Setting watermark defaults

        if w_type == 'text':
            watermark['w_text_knob'].setEnabled(True)
            watermark['wm_file'].setEnabled(False)
            watermark['opt_knob'].setValue(0)
            watermark['w_text_knob'].setValue(w_text) #This is the text knob string on group node
            watermark['wm_file'].setValue('')
            w_read['file'].setValue('')

            watermark['translate'].setValue([nuke.Root().width()/2, -nuke.Root().height()/2])
            watermark['rotate'].setValue(34)
            watermark['scale'].setValue(6.3)
            nuke.toNode('%s.Text1' % watermark.name())['box'].setT(nuke.Root().height())
            nuke.toNode('%s.Text1' % watermark.name())['box'].setY(nuke.Root().height()-101)
        elif w_type == 'image':
            watermark['wm_file'].setEnabled(True)
            watermark['w_text_knob'].setEnabled(False)
            watermark['opt_knob'].setValue(1)
            watermark['wm_file'].fromScript(w_file)
            w_read['file'].fromScript('[value parent.wm_file]')

            watermark['translate'].setValue([0, 0])
            watermark['rotate'].setValue(0)
            watermark['scale'].setValue(1)

        watermark['tiles'].setValue(7.4)
        watermark['opacity'].setValue(0.185)

        nuke.connectViewer( 0, watermark )

# Defining a callback
def knobChanged():
    n = nuke.thisNode()
    k = nuke.thisKnob()

    if k.name() == 'opt_knob':
        if k.value() == 'text':
            n.begin()
            nuke.toNode('watermark_image')['file'].setValue('')
            n.end()

            n['w_text_knob'].setEnabled(True)
            n['wm_file'].setEnabled(False)

            n['tiles'].setValue(7.4)
            n['translate'].setValue([nuke.Root().width()/2, -nuke.Root().height()/2])
            n['rotate'].setValue(34)
            n['scale'].setValue(6.3)
        elif k.value() == 'image':
            n.begin()

            nuke.toNode('watermark_image')['file'].fromScript('[value parent.wm_file]')
            n.end()
            n['w_text_knob'].setEnabled(False)
            n['wm_file'].setEnabled(True)

            n['tiles'].setValue(7.4)
            n['translate'].setValue([0, 0])
            n['rotate'].setValue(0)
            n['scale'].setValue(1)

#Adding callback
nuke.removeKnobChanged(knobChanged, nodeClass='dushyant_info_watermark_node')

nuke.addKnobChanged(knobChanged, nodeClass='dushyant_info_watermark_node')

def watermark_main(what, type, text, file, path):

    deselect()
    if len(what) == 0:
        nuke.message('Nothing selected')
        return
    for selected in what:
        if selected.Class() == 'Read':
            watermark_proc(selected, type, text, file, path)
        else:
            nuke.message( 'works only on read nodes, skipping %s' % selected['name'].getValue() )
    else:
        nuke.message('All done!')
