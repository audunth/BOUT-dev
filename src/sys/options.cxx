#include <boutexception.hxx>
#include <field_factory.hxx> // Used for parsing expressions
#include <options.hxx>
#include <output.hxx>
#include <utils.hxx>

#include <iomanip>
#include <sstream>

/// The source label given to default values
const std::string Options::DEFAULT_SOURCE{_("default")};
Options *Options::root_instance{nullptr};

Options &Options::root() {
  if (root_instance == nullptr) {
    // Create the singleton
    root_instance = new Options();
  }
  return *root_instance;
}

void Options::cleanup() {
  if (root_instance == nullptr)
    return;
  delete root_instance;
  root_instance = nullptr;
}

Options &Options::operator[](const std::string &name) {
  // Mark this object as being a section
  is_section = true;

  if (name.empty()) {
    return *this;
  }

  // Find and return if already exists
  auto it = children.find(lowercase(name));
  if (it != children.end()) {
    return it->second;
  }

  // Doesn't exist yet, so add
  std::string secname = name;
  if (!full_name.empty()) { // prepend the section name
    secname = full_name + ":" + secname;
  }

  // emplace returns a pair with iterator first, boolean (insert yes/no) second
  auto pair_it = children.emplace(lowercase(name), Options{this, secname});

  return pair_it.first->second;
}

const Options &Options::operator[](const std::string &name) const {
  TRACE("Options::operator[] const");
  
  if (!is_section) {
    throw BoutException(_("Option %s is not a section"), full_name.c_str());
  }

  if (name.empty()) {
    return *this;
  }

  // Find and return if already exists
  auto it = children.find(lowercase(name));
  if (it == children.end()) {
    // Doesn't exist
    throw BoutException(_("Option %s:%s does not exist"), full_name.c_str(), name.c_str());
  }

  return it->second;
}

bool Options::isSet() const {
  // Check if no value
  if (!is_value) {
    return false;
  }

  // Ignore if set from default
  if (bout::utils::variantEqualTo(attributes.at("source"), DEFAULT_SOURCE)) {
    return false;
  }

  return true;
}

template <> std::string Options::as<std::string>() const {
  if (!is_value) {
    throw BoutException(_("Option %s has no value"), full_name.c_str());
  }

  // Mark this option as used
  value_used = true;

  std::string result = bout::utils::variantToString(value);
  
  output_info << _("\tOption ") << full_name << " = " << result;
  if (attributes.count("source")) {
    // Specify the source of the setting
    output_info << " (" << bout::utils::variantToString(attributes.at("source")) << ")";
  }
  output_info << endl;

  return result;
}

template <> int Options::as<int>() const {
  if (!is_value) {
    throw BoutException(_("Option %s has no value"), full_name.c_str());
  }

  int result;

  if (bout::utils::holds_alternative<int>(value)) {
    result = bout::utils::get<int>(value);
    
  } else {
    // Cases which get a BoutReal then check if close to an integer
    BoutReal rval;
    
    if (bout::utils::holds_alternative<BoutReal>(value)) {
      rval = bout::utils::get<BoutReal>(value);
    
    } else if (bout::utils::holds_alternative<std::string>(value)) {
      // Use FieldFactory to evaluate expression
      // Parse the string, giving this Option pointer for the context
      // then generate a value at t,x,y,z = 0,0,0,0
      auto gen = FieldFactory::get()->parse(bout::utils::get<std::string>(value), this);
      if (!gen) {
        throw BoutException(_("Couldn't get integer from option %s = '%s'"),
                            full_name.c_str(), bout::utils::variantToString(value).c_str());
      }
      rval = gen->generate(0, 0, 0, 0);
    } else {
      // Another type which can't be converted
      throw BoutException(_("Value for option %s is not an integer"),
                            full_name.c_str());
    }
    
    // Convert to int by rounding
    result = ROUND(rval);
    
    // Check that the value is close to an integer
    if (fabs(rval - static_cast<BoutReal>(result)) > 1e-3) {
      throw BoutException(_("Value for option %s = %e is not an integer"),
                          full_name.c_str(), rval);
    }
  }

  value_used = true;

  output_info << _("\tOption ") << full_name << " = " << result;
  if (attributes.count("source")) {
    // Specify the source of the setting
    output_info << " (" << bout::utils::variantToString(attributes.at("source")) << ")";
  }
  output_info << endl;

  return result;
}

template <> BoutReal Options::as<BoutReal>() const {
  if (!is_value) {
    throw BoutException(_("Option %s has no value"), full_name.c_str());
  }

  BoutReal result;
  
  if (bout::utils::holds_alternative<int>(value)) {
    result = static_cast<BoutReal>(bout::utils::get<int>(value));
    
  } else if (bout::utils::holds_alternative<BoutReal>(value)) {
    result = bout::utils::get<BoutReal>(value);
      
  } else if (bout::utils::holds_alternative<std::string>(value)) {
    
    // Use FieldFactory to evaluate expression
    // Parse the string, giving this Option pointer for the context
    // then generate a value at t,x,y,z = 0,0,0,0
    std::shared_ptr<FieldGenerator> gen = FieldFactory::get()->parse(bout::utils::get<std::string>(value), this);
    if (!gen) {
      throw BoutException(_("Couldn't get BoutReal from option %s = '%s'"), full_name.c_str(),
                          bout::utils::get<std::string>(value).c_str());
    }
    result = gen->generate(0, 0, 0, 0);
  } else {
    throw BoutException(_("Value for option %s cannot be converted to a BoutReal"),
                        full_name.c_str());
  }
  
  // Mark this option as used
  value_used = true;
  
  output_info << _("\tOption ") << full_name << " = " << result;
  if (attributes.count("source")) {
    // Specify the source of the setting
    output_info << " (" << bout::utils::variantToString(attributes.at("source")) << ")";
  }
  output_info << endl;
  
  return result;
}

template <> bool Options::as<bool>() const {
  if (!is_value) {
    throw BoutException(_("Option %s has no value"), full_name.c_str());
  }
  
  bool result;
  
  if (bout::utils::holds_alternative<bool>(value)) {
    result = bout::utils::get<bool>(value);
  
  } else if(bout::utils::holds_alternative<std::string>(value)) {
    std::string strvalue = bout::utils::get<std::string>(value);
  
    char c = static_cast<char>(toupper((strvalue)[0]));
    if ((c == 'Y') || (c == 'T') || (c == '1')) {
      result = true;
    } else if ((c == 'N') || (c == 'F') || (c == '0')) {
      result = false;
    } else {
      throw BoutException(_("\tOption '%s': Boolean expected. Got '%s'\n"), full_name.c_str(),
                          strvalue.c_str());
    }
  } else {
    throw BoutException(_("Value for option %s cannot be converted to a bool"),
                        full_name.c_str());
  }
  
  value_used = true;
  
  output_info << _("\tOption ") << full_name << " = " << toString(result);
  
  if (attributes.count("source")) {
    // Specify the source of the setting
    output_info << " (" << bout::utils::variantToString(attributes.at("source")) << ")";
  }
  output_info << endl;

  return result;
}

void Options::printUnused() const {
  bool allused = true;
  // Check if any options are unused
  for (const auto &it : children) {
    if (it.second.is_value && !it.second.value_used) {
      allused = false;
      break;
    }
  }
  if (allused) {
    output_info << _("All options used\n");
  } else {
    output_info << _("Unused options:\n");
    for (const auto &it : children) {
      if (it.second.is_value && !it.second.value_used) {
        output_info << "\t" << full_name << ":" << it.first << " = "
                    << bout::utils::variantToString(it.second.value);
        if (it.second.attributes.count("source"))
          output_info << " (" << bout::utils::variantToString(it.second.attributes.at("source")) << ")";
        output_info << endl;
      }
    }
  }
  for (const auto &it : children) {
    if (it.second.is_section) {
      it.second.printUnused();
    }
  }
}

void Options::cleanCache() { FieldFactory::get()->cleanCache(); }

std::map<std::string, Options::OptionValue> Options::values() const {
  std::map<std::string, OptionValue> options;
  for (const auto& it : children) {
    if (it.second.is_value) {
      options.emplace(it.first, OptionValue{ bout::utils::variantToString(it.second.value),
                                              bout::utils::variantToString(it.second.attributes.at("source")),
                                              it.second.value_used});
    }
  }
  return options;
}

std::map<std::string, const Options *> Options::subsections() const {
  std::map<std::string, const Options *> sections;
  for (const auto &it : children) {
    if (it.second.is_section) {
      sections[it.first] = &it.second;
    }
  }
  return sections;
}
