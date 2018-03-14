#!/usr/bin/python3

# License of this file. This is also the license of the generated
# file.

print("""
/*!************************************************************************
 *
 * Wrapper for fields for different stagger locations
 *
 **************************************************************************
 * Copyright 2018
 *    B.D.Dudson, S.Farley, M.V.Umansky, X.Q.Xu, D. Schwörer
 *
 * Contact: Ben Dudson, bd512@york.ac.uk
 *
 * This file is part of BOUT++.
 *
 * BOUT++ is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * BOUT++ is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with BOUT++.  If not, see <http://www.gnu.org/licenses/>.
 *
 **************************************************************************/

""")

import jinja2
import itertools

# Get data from fieldops
import gen_fieldops as field

field3D = field.field3D
field2D = field.field2D
fieldperp = field.fieldperp
boutreal = field.boutreal

fields = [field3D, field2D, boutreal] ## fieldperp,


print("""
/*!************************************************************************
 * This file is autogenerated - see  flexible.hxx.in.py
 **************************************************************************/

#pragma once

#ifndef __FLEXIBLE_H__
#define __FLEXIBLE_H__

#include <bout_types.hxx>
#include <bout/deprecated.hxx>
#include <field2d.hxx>
#include <field3d.hxx>
#include <field_data.hxx>
#include <bout/dataiterator.hxx>
#include <boutexception.hxx>

const char * strLocation(CELL_LOC);
const Field2D interp_to(const Field2D&,CELL_LOC);
const Field3D interp_to(const Field3D&,CELL_LOC);

/// Template for having one field at different locations. If a Field
/// is not yet known for that location, it will be created and
/// cached. It is further possible to provide the staggered fields, if
/// it is e.g. crated from an analytical expression.
template <typename F>
class Flexible: public FieldData{
  typedef unsigned int uint;
public:
  Flexible(F & main){
    init(new F(main));
  };
  template <typename... Args>
  Flexible(Args... args) {
    F * main = new F(args...);
    init(main);
  }
  F & getNonConst(CELL_LOC loc_){
    if (loc_ == CELL_DEFAULT){
      return *fields[mainid];
    }
    uint loc=getId(loc_);
    if (fields[loc] == nullptr){
      // fields[0] is the field at CELL_CENTRE
      if (fields[0] == nullptr){
	fields[0]=new F(interp_to((*fields[mainid]),CELL_CENTRE));
	owner[mainid]=true;
      }
      if (loc != mainid) {
	fields[loc]=new F(interp_to(*fields[mainid],loc_));
	owner[mainid]=true;
      }
    }
    ASSERT1(fields[mainid]!=nullptr);
    return *fields[loc];
  };
  /// Get a const reference of the field at the specific location. If
  /// the CELL_LOC is CELL_DEFAULT the mainlocation will be returned.
  const F & get(CELL_LOC loc){
    return getNonConst(loc);
  };
  Flexible<F> & operator=(F& f) {
    set(f,true);
    ASSERT1(fields[mainid]!=nullptr);
    return *this;
  }
  Flexible<F> & operator=(F&& f) {
    set(f,true);
    ASSERT1(fields[mainid]!=nullptr);
    return *this;
  }
  Flexible<F> & operator=(BoutReal d) {
    (*fields[mainid])=d;
    clean(false);
    ASSERT1(fields[mainid]!=nullptr);
    return *this;
  }
  /// Set a part of the Flexible Field.
  /// If the main field is set, then, all other fields are
  /// invalidated. If an other location is set, then, it is assumed
  /// that the this is in sync with the main field.
  Flexible<F> & set(F & field, bool copy=true){
    uint loc = getId(field.getLocation());
    if (loc == mainid){
      clean(true);
    } else {
      if (fields[loc] != nullptr && owner[loc])
	delete fields[loc];
    }
    if (copy) {
      fields[loc]=new F(field);
    } else {
      fields[loc]=&field;
    }
    owner[loc]=copy; // did we just copy?
    return *this;
  };
  // Fallback to F - return the main field
  operator const F &() {
    return *fields[mainid];
  };
  // DEPRECATED? - do not know which stagger location
  const BoutReal & operator()(int x, int y) {
    return fields[mainid]->operator()(x,y);
  };
  // DEPRECATED? - do not know which stagger location
  const BoutReal & operator[](const DataIterator & i) {
    return fields[mainid]->operator[](i);
  };
  // DEPRECATED? - do not know which stagger location
  virtual inline const BoutReal & operator[](const Indices & i) const override {
    return fields[mainid]->operator[](i);
  };
  // DEPRECATED? - do not know which stagger location
  virtual inline BoutReal & operator[](const Indices & i) override {
    return fields[mainid]->operator[](i);
  };
  // FieldData stuff
  virtual void accept(FieldVisitor &v) override {
    fields[mainid]->accept(v);
  }
  virtual bool isReal() const override {
    return fields[mainid]->isReal();
  }
  virtual bool is3D() const override {
    return fields[mainid]->is3D();
  }
  virtual int byteSize() const override {
    return fields[mainid]->byteSize();
  }
  virtual int BoutRealSize() const override {
    return fields[mainid]->BoutRealSize();
  }
  virtual void doneComms() override {
    fields[mainid]->doneComms();
    clean(false);
  }; // Notifies that communications done
  virtual void applyBoundary(bool init=false) override {
    for (uint i=0;i<num_fields;++i){
      if (fields[i]){
	fields[i]->applyBoundary(init);
      }
    }
  }
  virtual void applyTDerivBoundary() override {
    throw BoutException("Flexible<F>: applyTDerivBoundary(): Not implemented");
  };
  void allocate() {
    fields[mainid]->allocate();
  }""")
template_inplace = jinja2.Template("""\
{% if field == 'BoutReal' %}\
  Flexible<F>& operator{{operator}}=({{field}} rhs) {
    fields[mainid]->operator{{operator}}=(rhs);
    clean(false);
    return *this;
  };
{% else %}\
  Flexible<F>& operator{{operator}}=(const {{field}} & rhs) {
    if (mainid == getId(rhs.getLocation())){
      fields[mainid]->operator{{operator}}=(rhs);
    } else {
      throw BoutException("Trying to update a Flexible<F>, but the\
main location of Flexible<F> is different to the location of the rhs.\\n\
Flexible<F> is at %s, but rhs is at %s",strLocation(mainLocation()),
strLocation(rhs.getLocation()));
    }
    clean(false);
    return *this;
  };
{% endif %}\
""")
for operator, operator_name in field.operators.items():
    for rhs in fields:
        print(template_inplace.render(operator=operator,field=rhs),end='')
print("""
private:
  // Helper function to get index of location.
  uint getId(CELL_LOC loc_){
    uint loc = static_cast<uint>(loc_)-1;
    if ( loc > num_fields || loc_ == 0){
      throw BoutException("Unexpected Fieldlocation!\\n (Info: I got %d - %s)",loc,strLocation(loc_));
    }
    return loc;
  };
  void init(F * main){
    mainid = getId(main->getLocation());
    for (uint i=0;i<num_fields;++i){
      fields[i]=nullptr;
    }
    fields[mainid]=main;
    owner[mainid]=true;
  };
  void clean(bool include_main){
    for (uint i=0;i<num_fields;i++){
      if (i != mainid || include_main) {
        if (fields[i] != nullptr){
	  if (owner[i]){
	    delete fields[i];
	  }
	  fields[i]=nullptr;
        }
      }
    }
  };
  // get the mainlocation
  CELL_LOC mainLocation(){
    return (CELL_LOC)(mainid+1);
  };
  // Number of field locations we support
  static const uint num_fields=4;
  // The pointers to the fields. Some may be null
  F * fields[num_fields];
  // Are we the owner of the fields?
  bool owner[num_fields];
  // The id of the mainlocation
  uint mainid;
};


""")

# Code-Template in the case the the flexible field is on the rhs of the operation.
# The case of a BoutReal needs to be handled separately.
# Note the case to update a lhs inplace is not supported yet - this
# needs to be declared int the specific fields.
template_rhs = jinja2.Template("""\
{% if lhs == 'BoutReal' %}\

{{template}} {{out}} operator{{operator}}({{lhs}} lhs, Flexible<{{rhs}}> &rhs) {
  return lhs {{operator}} rhs.get(CELL_DEFAULT);
};
{% else %}\

{{template}} {{out}} operator{{operator}}(const {{lhs}} &lhs, Flexible<{{rhs}}> &rhs) {
  return lhs {{operator}} rhs.get(lhs.getLocation());
};
{% endif %}\
{% if lhs == out and False %}\
{{template}}//{{out}} & {{lhs}}::operator{{operator}}=( Flexible<{{rhs}}> &rhs) {
  return this->operator {{operator}}= (rhs.get(lhs.getLocation()));
};
{% endif %}\
""")
# Same as above for the flexible field being the lhs of the operation
# inplace operations are handeled above
template_lhs = jinja2.Template("""\
{% if rhs == 'BoutReal' %}\

{{template}} {{out}} operator{{operator}}(Flexible<{{lhs}}> &lhs, {{rhs}} rhs) {
  return lhs.get(CELL_DEFAULT) {{operator}} rhs;
};
{% else %}\

{{template}} {{out}} operator{{operator}}(Flexible<{{lhs}}> &lhs, const {{rhs}} &rhs) {
  return lhs.get(rhs.getLocation()) {{operator}} rhs;
};
{% endif %}\
""");

# If everything is the same, we can use C++ templates
for operator, operator_name in field.operators.items():
    template_args = {
        'template': 'template <typename F>\n',
        'operator': operator,
        'out': 'F',
        'lhs': 'F',
        'rhs': 'F',
    }
    print(template_lhs.render(**template_args),end='')
    print(template_rhs.render(**template_args),end='')

for lhs, rhs in itertools.product(fields, fields):
    # We don't have to define F F operations - done above via C++
    # templates
    if lhs == rhs :
        continue
    out = field.returnType(rhs, lhs)

    for operator, operator_name in field.operators.items():

        template_args = {
            'template': 'inline',
            'operator': operator,
            'out': out,
            'lhs': lhs,
            'rhs': rhs,
        }
        # only render templates if we are not wrapping a BoutReal
        if lhs != "BoutReal":
            print(template_lhs.render(**template_args),end='')
        if rhs != "BoutReal":
            print(template_rhs.render(**template_args),end='')


# end of header file
print("""

#endif""")
