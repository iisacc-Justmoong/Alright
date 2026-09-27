# Swift emits dSYM beside the executable. Keep debugging data outside signed bundles.
if(EXISTS "${SOURCE}")
    get_filename_component(parent "${DESTINATION}" DIRECTORY)
    file(MAKE_DIRECTORY "${parent}")
    file(REMOVE_RECURSE "${DESTINATION}")
    file(RENAME "${SOURCE}" "${DESTINATION}")
endif()
