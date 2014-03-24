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

#!/usr/bin/env/python

import os
import glob

gplv2orlater = """# This program is free software; you can redistribute it and/or
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

"""

def check_file(fname):
    print "checking %s" % fname
    assert os.path.exists(fname)
    f = open(fname, 'r')
    c = "".join(f.readlines())
    f.close()
    if not c.startswith(gplv2orlater):
        f = open(fname, 'w')
        f.write(gplv2orlater)
        f.write(c)
        f.close()

def check_directory(arg, dirname, name):
    for fname in sorted(glob.glob("%s/*.py" % dirname)):
        check_file(fname)

if __name__ == "__main__":
    os.path.walk("../", check_directory, "") 
