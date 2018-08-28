"""
 * ***** BEGIN GPL LICENSE BLOCK *****
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 *
 * Contributor(s): Julien Duroure.
 *
 * ***** END GPL LICENSE BLOCK *****
 * This development is done in strong collaboration with Airbus Defence & Space
 """

from mathutils import Matrix, Vector, Quaternion

class Conversion():
    def __init__(self):
        pass


    @staticmethod
    def matrix(mat_input):
        mat =  Matrix([mat_input[0:4], mat_input[4:8], mat_input[8:12], mat_input[12:16]])
        mat.transpose()

        return mat

    def quaternion(self, q):
        return Quaternion([q[3], q[0], q[1], q[2]])

    def matrix_quaternion(self, q):
        return Quaternion([q[0], q[1], q[2], q[3]])

    def location(self, location):
        return location

    def scale(self, scale):
        return scale
