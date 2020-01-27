"""
A class to represent a transformation between two 2-dimensional coordinate
   systems. Supports transforming points, calculating the transformation from
   various formats if input information and combining separate transformations.

Recommended usage is to name transformations by their action, e.g.
   robot_to_panel = Transform2D(...)
   my_panel_points = robot_to_panel.transform(my_robot_points)


Copyright (c) 2019, OptoFidelity OY

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    3. All advertising materials mentioning features or use of this software must display the following acknowledgement: This product includes software developed by the OptoFidelity OY.
    4. Neither the name of the OptoFidelity OY nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import math
from collections import Iterable

class Transform2D:
    '''A transformation between two 2D coordinate systems. Can include
    translation, rotation and scaling.'''
    def __init__(self, matrix):
        '''Initialize the transformation from a 2x3 matrix. Argument must be of
        form [[x1, x2, x3], [y1, y2, y3]].'''
        assert len(matrix) == 2 and len(matrix[0]) == 3 and len(matrix[1]) == 3
        self.matrix = matrix
    
    @classmethod
    def identity(cls):
        '''Identity transform - does nothing'''
        return cls([[1, 0, 0], [0, 1, 0]])  

    @classmethod
    def offset(cls, x, y):
        '''Translation (i.e. simple move) of the coordinate system.'''
        return cls([[1, 0, x], [0, 1, y]])
    
    @classmethod
    def scale(cls, scale_x, scale_y):
        '''Scaling of coordinate axes.'''
        return cls([[scale_x, 0, 0], [0, scale_y, 0]])
    
    @classmethod
    def rotate_radians(cls, angle):
        '''Rotate the coordinate system. Positive direction is
        counter-clockwise. Angle is in radians.'''
        return cls([[math.cos(angle), -math.sin(angle), 0],
                    [math.sin(angle), math.cos(angle), 0]])
    
    @classmethod
    def rotate_degrees(cls, angle):
        '''Rotate the coordinate system. Positive direction is
        counter-clockwise. Angle is in degrees.'''
        return cls.rotate_radians(math.radians(angle))
    
    def transform(self, points):
        '''Transform a group of points, or a single point. Argument can be list
        of tuples [(x,y), (x,y), (x,y)] or a single tuple (x,y).'''

        assert isinstance(points, Iterable)

        # Handle empty list
        if len(points) == 0:
            return points
        
        if isinstance(points[0], Iterable):
            return [self.transform(p) for p in points]
        else:
            x, y = points
            x2 = self.matrix[0][0] * x + self.matrix[0][1] * y + self.matrix[0][2]
            y2 = self.matrix[1][0] * x + self.matrix[1][1] * y + self.matrix[1][2]
            return (x2, y2)
    
    def invert(self):
        '''Returns the inverse of the transform.'''
        raise Exception("Inversion not implemented (correctly)")
        # TODO: The following implementation is broken -> it does not handle correctly the
        # constant part (tx, ty) -> they cannot be directly copied as it is done here   
        # p2 = R * p + T  <=>   p = Rinv * p2 - Rinv * T
        a, b, c, d = self.matrix[0][0], self.matrix[0][1], self.matrix[1][0], self.matrix[1][1]
        determinant = a * d - b * c
        if determinant == 0:
            raise Exception("Transform2D is not invertible!")
        
        scale = 1.0 / determinant
        new_rotation = Transform2D([[d * scale, -b * scale, 0], [-c * scale, a * scale, 0]])
        tx, ty = new_rotation.transform((self.matrix[0][2], self.matrix[1][2]))
        new_rotation.matrix[0][2] = -tx
        new_rotation.matrix[1][2] = -ty
        return new_rotation
    
    def __add__(self, other):
        # p2 = R1 * p + T
        # p3 = R2 * p2 + T2
        # => p3 = R2 * R1 * p + R2 * T + T2
    
        assert isinstance(other, Transform2D)

        a1, b1, c1, d1 = self.matrix[0][0], self.matrix[0][1], self.matrix[1][0], self.matrix[1][1]
        a2, b2, c2, d2 = other.matrix[0][0], other.matrix[0][1], other.matrix[1][0], other.matrix[1][1]
        tx, ty = other.transform((self.matrix[0][2], self.matrix[1][2]))
        new = Transform2D([[a1 * a2 + b2 * c1, a2 * b1 + b2 * d1, tx], [c2 * a1 + d2 * c1, c2 * b1 + d2 * d1, ty]])
        return new
    
    def __str__(self):
        return "Transform2D(" + str(self.matrix) + ")"


    