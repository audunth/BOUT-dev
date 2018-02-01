#!/usr/bin/env python3
"""Code-generator for arithmetic operators on Field2Ds/Field3Ds

This uses the jinja template in gen_fieldops.jinja to generate code
for the arithmetic operators, and prints to stdout.

The `Field` class provides some helper functions for determining how to
pass a variable by reference or pointer, and how to name arguments in
function signatures. This allows us to push some logic into the
templates themselves.

"""


from __future__ import print_function

try:
    from builtins import object
except ImportError:
    pass

from collections import OrderedDict
from copy import deepcopy as copy
import itertools

try:
    import jinja2
except ImportError:
    raise ImportError('Missing Python module "jinja2". See "Field2D/Field3D Arithmetic '
                      'Operators" in the BOUT++ user manual for more information')

# The arthimetic operators
# OrderedDict to (try to) ensure consistency between python 2 & 3
operators = OrderedDict([
    ('*', 'multiplication'),
    ('/', 'division'),
    ('+', 'addition'),
    ('-', 'subtraction'),
])

header = """// This file is autogenerated - see gen_fieldops.py
#include <bout/mesh.hxx>
#include <field2d.hxx>
#include <field3d.hxx>
#include <globals.hxx>
#include <interpolation.hxx>
"""


class Field(object):
    """Abstracts over BoutReals and Field2D/3D/Perps

    Provides some helper functions for writing function signatures and
    passing data

    """

    def __init__(self, field_type, dimensions, name=None):
        # C++ type of the field, e.g. Field3D
        self.field_type = field_type
        # array: dimensions of the field
        self.dimensions = dimensions
        # name of this field
        self.name = name

    @property
    def passByReference(self):
        """Returns "Type& name", except if field_type is BoutReal,
        in which case just returns "Type name"

        """
        return "{self.field_type}{ref} {self.name}".format(
            self=self, ref="&" if self.field_type != "BoutReal" else "")

    @property
    def passBoutRealPointer(self):
        """Returns "BoutReal* name", except if field_type is BoutReal,
        in which case just returns "BoutReal name"

        Also adds "__restrict__" attribute if `for_gcc` is True
        """
        return "BoutReal {ref}{restrict} {self.name}".format(
            self=self, ref="*" if self.field_type != "BoutReal" else "",
            restrict="__restrict__" if for_gcc and self.field_type != "BoutReal" else "")

    @property
    def getPointerToData(self):
        """Returns a pointer to the underlying data, e.g. `&Field3D[i]`,
        except for plain BoutReals"""
        if self.field_type == 'BoutReal':
            return self.name
        return "&{}[i]".format(self.name)

    def getElement(self, data=True):
        """Get an element in the field, either using C-loop style index (default),
        or with an `Indices` object (if `data=False`)

        """

        if self.field_type == 'BoutReal':
            return self.name
        if data:
            if self.field_type == 'Field2D':
                index = "y + x*ny"
            elif self.field_type == 'FieldPerp':
                index = "z + x*nz"
            elif self.field_type == 'Field3D':
                index = "z + nz*(y + ny*x)"
            else:
                raise ValueError("Unexpected field_type")
        else:
            index = "i"
        return "{name}[{index}]".format(name=self.name, index=index)

    def __eq__(self, other):
        try:
            return self.field_type == other.field_type
        except AttributeError:
            return self.field_type == other

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return "Field({}, {}, {})".format(self.field_type, self.dimensions, self.name)

    def __str__(self):
        return self.field_type


# Declare what fields we currently support:
# Field perp is currently missing
field3D = Field('Field3D', ['x', 'y', 'z'])
field2D = Field('Field2D', ['x', 'y'])
boutreal = Field('BoutReal', [])
fields = [field3D, field2D, boutreal]


def returnType(f1, f2):
    """Determine a suitable return type, by seeing which field is 'larger'.

    """
    if f1 == f2:
        return copy(f1)
    elif f1 == 'BoutReal':
        return copy(f2)
    elif f2 == 'BoutReal':
        return copy(f1)
    else:
        return copy(field3D)


if __name__ == "__main__":
    for_gcc = True
    print(header)

    env = jinja2.Environment(loader=jinja2.FileSystemLoader('.'),
                             trim_blocks=True)

    template = env.get_template("gen_fieldops.jinja")

    for lhs, rhs in itertools.product(fields, fields):
        # We don't have define real real operations
        if lhs == rhs == 'BoutReal':
            continue
        rhs = copy(rhs)
        lhs = copy(lhs)

        # If both fields are the same, or one of them is real, we
        # don't need to care what element is stored where, but can
        # just loop directly over everything, using a simple c-style
        # for loop. Otherwise we need x,y,z of the fields.
        elementwise = lhs != rhs and lhs != 'BoutReal' and rhs != 'BoutReal'

        # The output of the operation. The `larger` of the two fields.
        out = returnType(rhs, lhs)
        out.name = 'result'
        lhs.name = 'lhs'
        rhs.name = 'rhs'

        # Depending on how we loop over the fields, we need to know
        # x, y and z, or just the total number of elements
        if elementwise:
            length_arg = ",".join(["int n{}".format(d) for d in out.dimensions])
            dims = OrderedDict([("n" + x, x) for x in out.dimensions])
        else:
            length_arg = "int len"
            dims = {"len": 'i'}

        # Either total number of elements, or size of each dimension separately
        non_compound_length_dims = ["localmesh->LocalN{}".format(d) for d in out.dimensions]
        compound_length_dims = ["fieldmesh->LocalN{}".format(d) for d in out.dimensions]

        for operator, operator_name in operators.items():

            template_args = {
                'operator': operator,
                'operator_name': operator_name,
                'elementwise': elementwise,
                'dims': dims,

                'out': out,
                'lhs': lhs,
                'rhs': rhs,

                'non_compound_length_dims': non_compound_length_dims,
                'compound_length_dims': compound_length_dims,
                'length_arg': length_arg,
            }

            print(template.render(**template_args))
