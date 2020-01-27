"""
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
import cv2
import numpy as np
import logging
from xml.dom.minidom import parseString as minidom_parseString
from svgpathtools.svg2paths import polyline2pathd, parse_path, svg2paths


log = logging.getLogger(__name__)


class SvgRegion:
    """
    Use svg vector graphic file to describe DUT shape.
    - test if points are inside or outside of a test region
    - test if a shape can be drawn on screen to certain place
    - etc.

    The svg file should include at least shapes with name
        'test_region': the area that can be touched with robot finger
        'analysis_region: the area that should be included in analysis
        'bounds': the rectangular area containing the screen completely
    """
    def __init__(self):
        self.bounding_box = None
        self.region = {}

    def load_file(self, filename):
        """
        Load a svg file with filename
        :param filename: filename with path
        """
        paths, attributes = svg2paths(filename)
        self._load_svg(paths, attributes)

    def load_string(self, svg_string):
        """
        Load a svg file from string
        :param svg_string: svg file as string
        """
        paths, attributes = self.__svgstring2paths(svg_string)
        self._load_svg(paths, attributes)

    def _load_svg(self, paths, attributes):
        """
        The actual load function
        Loads the needed regions to member variables

        :param paths: svg paths in svgpathtools internal paths type
        :param attributes: svg attributes in svgpathtools internal paths type
        """

        # get REGION, BOUNDS from svg
        bounding_box = None
        self.region = {}

        def bounds(path):
            x0, x1, y0, y1 = path.bbox()
            return x0, y0, x1, y1

        def join_bounds(b0, b1):
            xcoords = np.array([b0[0], b0[2], b1[0], b1[2]])
            ycoords = np.array([b0[1], b0[3], b1[1], b1[3]])
            x0 = float(np.min(xcoords))
            x1 = float(np.max(xcoords))
            y0 = float(np.min(ycoords))
            y1 = float(np.max(ycoords))
            return x0, y0, x1, y1

        for p, a in zip(paths, attributes):
            rid = a.get('id', "")

            self.region[rid] = p
            if bounding_box is None:
                bounding_box = bounds(p)
            else:
                bounding_box = join_bounds(bounding_box, bounds(p))

        # translate to x/y 0,0 origin
        for region_id in self.region:
            self.region[region_id] = self.region[region_id].translated(complex(-bounding_box[0], -bounding_box[1]))

        bounding_box = [0, 0, bounding_box[2] - bounding_box[0], bounding_box[3] - bounding_box[1]]
        self.bounding_box = bounding_box

    @staticmethod
    def __svgstring2paths(svg_string,
                          convert_lines_to_paths=True,
                          convert_polylines_to_paths=True,
                          convert_polygons_to_paths=True,
                          return_svg_attributes=False):
        """
        Not in svgpathtools so added here as private function

        Converts an SVG string into a list of Path objects and a list of
        dictionaries containing their attributes.  This currently supports
        SVG Path, Line, Polyline, and Polygon elements.
        This function originally missing from SvgPathTools, added for dut purposes
        :param svg_string: the location of the svg file
        :param convert_lines_to_paths: Set to False to disclude SVG-Line objects
        (converted to Paths)
        :param convert_polylines_to_paths: Set to False to disclude SVG-Polyline
        objects (converted to Paths)
        :param convert_polygons_to_paths: Set to False to disclude SVG-Polygon
        objects (converted to Paths)
        :param return_svg_attributes: Set to True and a dictionary of
        svg-attributes will be extracted and returned
        :return: list of Path objects, list of path attribute dictionaries, and
        (optionally) a dictionary of svg-attributes

        """
        doc = minidom_parseString(svg_string)

        def dom2dict(element):
            """Converts DOM elements to dictionaries of attributes."""
            keys = list(element.attributes.keys())
            values = [val.value for val in list(element.attributes.values())]
            return dict(list(zip(keys, values)))

        # Use minidom to extract path strings from input SVG
        paths = [dom2dict(el) for el in doc.getElementsByTagName('path')]
        d_strings = [el['d'] for el in paths]
        attribute_dictionary_list = paths
        # if pathless_svg:
        #     for el in doc.getElementsByTagName('path'):
        #         el.parentNode.removeChild(el)

        # Use minidom to extract polyline strings from input SVG, convert to
        # path strings, add to list
        if convert_polylines_to_paths:
            plins = [dom2dict(el) for el in doc.getElementsByTagName('polyline')]
            d_strings += [polyline2pathd(pl['points']) for pl in plins]
            attribute_dictionary_list += plins

        # Use minidom to extract polygon strings from input SVG, convert to
        # path strings, add to list
        if convert_polygons_to_paths:
            pgons = [dom2dict(el) for el in doc.getElementsByTagName('polygon')]
            d_strings += [polyline2pathd(pg['points']) + 'z' for pg in pgons]
            attribute_dictionary_list += pgons

        if convert_lines_to_paths:
            lines = [dom2dict(el) for el in doc.getElementsByTagName('line')]
            d_strings += [('M' + l['x1'] + ' ' + l['y1'] +
                           'L' + l['x2'] + ' ' + l['y2']) for l in lines]
            attribute_dictionary_list += lines

        # if pathless_svg:
        #     with open(pathless_svg, "wb") as f:
        #         doc.writexml(f)

        if return_svg_attributes:
            svg_attributes = dom2dict(doc.getElementsByTagName('svg')[0])
            doc.unlink()
            path_list = [parse_path(d) for d in d_strings]
            return path_list, attribute_dictionary_list, svg_attributes
        else:
            doc.unlink()
            path_list = [parse_path(d) for d in d_strings]
            return path_list, attribute_dictionary_list

    @property
    def size(self):
        """
        dut size as width, height in millimeters
        uses the 'bounding_box' region
        :return: width, height
        """
        if self.bounding_box is None:
            return 0, 0
        return self.bounding_box[2], self.bounding_box[3]

    @staticmethod
    def region_to_contour(region, numpoints=100):
        """
        Create OpenCV-compatible contour
        Can be used for region comparison functions in OpenCV
        Can be used to draw the region to bitmap with OpenCV

        :param region: region to convert
        :param numpoints: number of points in contour
        :return: the contour, numpy array of numpy.float32 values
        """
        contour = []
        for t in np.linspace(0.0, 1.0, numpoints):
            pt = region.point(t)
            pt = pt.real, pt.imag
            contour.append(pt)
        contour = np.array(contour)
        contour = np.round(contour, 4).astype(np.float32) # conversion a must, otherwise unknown funny type
        return contour

    def region_str_to_contour(self, region_str):
        """
        Create OpenCV-compatible contour for specified region
        :param region_str: region name as string
        :return: contour
        """
        region = self.region[region_str]
        return self.region_to_contour(region)

    def filter_points(self, points, region, margin):
        """
        Filter list of points that fit inside given region with given margin
        :param points: list of (x, y) points
        :param region: region to use
        :param margin: margin to add inside the region
        :return: list of points inside the given region
        """
        contour = self.region_to_contour(region, 2000)
        results = []
        for pt in points:
            if cv2.pointPolygonTest(contour, tuple(pt), True) >= margin:
                results.append(pt)
        return results

    def filter_points_contour(self, points, margin, contour):
        """
        Filter points based on the given contour. With this one can save
        the contour elsewhere and then do the filtering faster
        :param points: list of points[(x1, y1), (x2, y2),...]
        :param margin: margin to add inside the region
        :param contour: OpenCV-compatible contour
        :return: filtered list of points
        """
        results = []
        for pt in points:
            if cv2.pointPolygonTest(contour, tuple(pt), True) >= margin:
                results.append(pt)
        return results


    def filter_points_str_region(self, points, region_str, margin):
        """
        Filter list of points that fit inside given region with given margin
        :param points: list of (x, y) points
        :param region: name of the region to use
        :param margin: margin to add inside the region
        :return: list of points inside the given region
        """
        region = self.region[region_str]
        return self.filter_points(points, region, margin)


    def filter_line(self, line, contour, margin):
        """
        Filter line and give back pieces that are inside the given region with given margin
        :param line: (start x, start y, end x, end y)
        :param contour: contour to use as filter (use region_to_contour to use with regions)
        :param margin: margin to add inside the contour
        :return: list of lines inside the given contour after cutting with the given contour.
        """

        # resolution of the filtering, in millimeters
        # changing this affects accuracy and speed of the operation
        mm_resolution = 0.001

        p0 = np.array([line[0], line[1]])
        p1 = np.array([line[2], line[3]])
        line_len = np.linalg.norm(p1-p0)

        # line unit vector
        pv = (p1-p0) / line_len

        pos = 0
        end_pos = line_len

        lp0 = None
        lp1 = None
        lines = []
        while True:
            # current point on the line
            pt = p0 + pos * pv
            distance_to_shape = cv2.pointPolygonTest(contour, tuple(pt), True)
            if distance_to_shape >= margin:
                # we are inside the shape by margin
                if lp0 is None:
                    lp0 = pt
                else:
                    lp1 = pt
            else:
                # we are outside of the shape by margin
                if lp1 is not None:
                    lines.append((lp0[0], lp0[1], lp1[0], lp1[1]))
                lp0 = None
                lp1 = None

            # it is safe to skip at least to next margin of distance (-mm_resolution, which is added anyways)
            skip = abs(distance_to_shape) - margin - mm_resolution
            if skip > 0:
                pos += skip

            # advance on the line
            pos += mm_resolution

            if pos > end_pos:
                break

        # just one more line possible
        if lp1 is not None:
            lines.append((lp0[0], lp0[1], lp1[0], lp1[1]))
        return lines

    def filter_lines(self, lines, region, margin):
        """
        Filter list of lines so that only pieces inside the given region are left.
        :param lines: list of lines [(start x, start y, end x, end y)]
        :param region: region to use for filtering
        :param margin: margin to add inside the region
        :return: list of list of lines. Every given line results as list of (zero or more) lines.
        """
        contour = self.region_to_contour(region, 2000)
        results = []
        for line in lines:
            results.append(self.filter_line(line, contour, margin))
        return results

    def filter_lines_str_region(self, lines, region_str, margin):
        """
        Filter list of lines so that only pieces inside the given region are left.
        :param lines: list of lines [(start x, start y, end x, end y)]
        :param region: name of the region to use for filtering
        :param margin: margin to add inside the region
        :return: list of list of lines. Every given line results as list of (zero or more) lines.
        """
        region = self.region[region_str]
        return self.filter_lines(lines, region, margin)
