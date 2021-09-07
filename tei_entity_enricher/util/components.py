import os

import pandas as pd
import streamlit as st
#from streamlit.widgets import NoValue
from st_aggrid import AgGrid
from tei_entity_enricher.util.helper import local_save_path, state_ok, state_failed, state_uncertain


def editable_single_column_table(entry_list, key, head, openentrys=100, height=150, width=1, reload=False):
    if key in st.session_state and st.session_state[key] is not None:
        init_list=[]
        for ent_dictio in st.session_state[key]["rowData"]:
            content=ent_dictio[head]
            if content is not None and content!="":
                init_list.append(content)
        init_value=pd.DataFrame({head: init_list + [""] * openentrys})  # input_dataframe,
    else:
        init_value=pd.DataFrame({head: entry_list + [""] * openentrys})  # input_dataframe,
    response = AgGrid(
        init_value,
        height=height,
        editable=True,
        sortable=False,
        filter=False,
        resizable=True,
        defaultWidth=width,
        fit_columns_on_grid_load=True,
        key=key,
        reload_data=reload
    )
    st.info("Edit the table by double-click in it and press Enter after changing a cell.")
    returnlist = []
    if "data" in response:
        all_list = list(response["data"].to_dict()[head].values())
        for element in all_list:
            if element != "" and element is not None and element != "nan":
                returnlist.append(element)
    return returnlist


def editable_multi_column_table(entry_dict, key, openentrys=100, height=150, width=1, reload=False):
    in_data = entry_dict.copy()
    max_len = openentrys
    for entry_dict_key in in_data.keys():
        if len(in_data[entry_dict_key]) > max_len:
            max_len = len(in_data[entry_dict_key])
    for entry_dict_key in in_data.keys():
        # in_data[entry_dict_key]=in_data[entry_dict_key] + [''] * (max_len-len(in_data[entry_dict_key]))
        # in_data[entry_dict_key].extend([''] * (max_len-len(in_data[entry_dict_key])))
        keylist = in_data[entry_dict_key].copy()
        keylist.extend([""] * (max_len - len(in_data[entry_dict_key])))
        in_data[entry_dict_key] = keylist

    response = AgGrid(
        pd.DataFrame(in_data),  # input_dataframe,
        height=height,
        editable=True,
        sortable=False,
        filter=False,
        resizable=True,
        defaultWidth=width,
        fit_columns_on_grid_load=True,
        key=key,
        reload_data=reload
    )
    st.info("Edit the table by double-click in it and press Enter after changing a cell.")
    if "data" in response:
        answer_dict = response["data"].to_dict()
        returndict = {}
        for key in answer_dict:
            answer_dict[key] = list(answer_dict[key].values())
            returndict[key] = []
        for i in range(max_len):
            needed = False
            for key in answer_dict:
                if answer_dict[key][i] is not None and answer_dict[key][i] != "" and answer_dict[key][i] != "nan":
                    needed = True
            if needed:
                for key in answer_dict:
                    if key == "nan":
                        returndict[""].append(answer_dict[key][i])
                    elif answer_dict[key][i] == "nan":
                        returndict[key].append("")
                    else:
                        returndict[key].append(answer_dict[key][i])
        return returndict
    return entry_dict


def file_selector_expander(folder_path="", target="Select file...", init_file=""):
    with st.expander(target, expanded=False):
        selected_file = file_selector(folder_path, parent=target, init_file=init_file)
    return selected_file


def dir_selector_expander(folder_path="", target="Select directory..."):
    with st.expander(target):
        selected_dir = dir_selector(folder_path, parent=target)
    return selected_dir


def file_selector(folder_path="", sub_level=0, max_level=10, parent="", init_file=""):
    filenames = [
        f for f in os.listdir(os.path.join(os.getcwd(), folder_path)) if not f[0] == "."
    ]  # get file names from dir excluding hidden files
    a, b = st.columns([sub_level + 1, 2 * max_level])
    if os.path.isfile(os.path.join(folder_path, init_file)) and os.path.isdir(os.path.join(os.getcwd(), folder_path)):
        # norm_init_file = os.path.normpath(init_file)
        init_file_lst = init_file.split(os.sep)
        try:
            index = filenames.index(init_file_lst[0])
            if len(init_file_lst[1:]):
                init_file = os.path.join(*init_file_lst[1:])
        except ValueError:
            index = 0
    else:
        index = 0

    selected_filename = b.selectbox(f"{folder_path}", filenames, index=index, key=f"{parent}{folder_path}")
    if selected_filename is None:
        return None
    abs_path = os.path.join(folder_path, selected_filename)
    if os.path.isdir(abs_path):
        return file_selector(
            abs_path,
            sub_level=sub_level + 1 if sub_level < max_level else sub_level,
            max_level=max_level,
            parent=parent,
            init_file=init_file,
        )
    return os.path.join(folder_path, selected_filename)


def dir_selector(folder_path="", sub_level=0, max_level=10, parent=""):
    filenames = [
        f
        for f in os.listdir(os.path.join(os.getcwd(), folder_path))
        if not f[0] == "." and os.path.isdir(os.path.join(folder_path, f))
    ]  # get file names from dir excluding hidden files
    a, b, c = st.columns([sub_level + 1, 2 * max_level, 2])
    selected_dirname = b.selectbox(f"{folder_path}", filenames, key=f"{parent}{folder_path}")
    if selected_dirname is None:
        return None
    abs_path = os.path.join(folder_path, selected_dirname)
    if os.path.isdir(abs_path):
        c.text("")
        c.text("")
        if c.button("apply", key=f"{parent}{folder_path}"):
            return abs_path

        return dir_selector(
            abs_path, sub_level=sub_level + 1 if sub_level < max_level else sub_level, max_level=max_level
        )
    return os.path.join(folder_path, selected_dirname)


@st.cache(allow_output_mutation=True)
def get_sel_dict():
    return dict()


def small_dir_selector(label=None, value=local_save_path, key="", help=None, return_state=False, ask_make=False):
    sel_dict = get_sel_dict()
    col1, col2 = st.columns([10, 1])
    col3, col4, col5 = st.columns([25, 25, 50])
    dirpath_placeholder = col1.empty()
    state_placeholder = col2.empty()
    parent_button_placeholder = col3.empty()
    subelement_button_placeholder = col4.empty()
    chosen_subdir_placeholder = col5.empty()
    dirpath = dirpath_placeholder.text_input(label=label, value=value, key=key + "_text_input", help=help)
    if dirpath != value:
        dirpath = dirpath_placeholder.text_input(label=label, value=dirpath, key=key + "_text_input", help=help)
    if os.path.isdir(dirpath):
        state_placeholder.latex(state_ok)
        ret_state = state_ok
        if parent_button_placeholder.button(
            "Go to parent directory", key=key + "_level_up", help="Go one directory up."
        ):
            dirpath = os.path.dirname(dirpath)
            sel_dict[key + "_chosen_subdir"] = None
            dirpath = dirpath_placeholder.text_input(label=label, value=dirpath, key=key + "_text_input", help=help)
        subdirlist = [name for name in os.listdir(dirpath) if os.path.isdir(os.path.join(dirpath, name))]
        if len(subdirlist) > 0:
            if key + "_chosen_subdir" not in sel_dict.keys():
                sel_dict[key + "_chosen_subdir"] = None
            sel_dict[key + "_chosen_subdir"] = chosen_subdir_placeholder.selectbox(
                "Subdirectories:",
                subdirlist,
                subdirlist.index(sel_dict[key + "_chosen_subdir"])
                if sel_dict[key + "_chosen_subdir"] and sel_dict[key + "_chosen_subdir"] in subdirlist
                else 0,
                key=key + "_chosen_subdir",
            )
            if subelement_button_placeholder.button(
                "Go to subdirectory:", key=key + "_go_to", help="Go to the chosen subdirectory."
            ):
                dirpath = os.path.join(dirpath, sel_dict[key + "_chosen_subdir"])
                sel_dict[key + "_chosen_subdir"] = None
                dirpath = dirpath_placeholder.text_input(label=label, value=dirpath, key=key + "_text_input", help=help)
                subdirlist = [name for name in os.listdir(dirpath) if os.path.isdir(os.path.join(dirpath, name))]
                if len(subdirlist) > 0:
                    sel_dict[key + "_chosen_subdir"] = chosen_subdir_placeholder.selectbox(
                        "Subdirectories:",
                        subdirlist,
                        subdirlist.index(sel_dict[key + "_chosen_subdir"])
                        if sel_dict[key + "_chosen_subdir"] and sel_dict[key + "_chosen_subdir"] in subdirlist
                        else 0,
                        key=key + "_chosen_subdir",
                    )
                else:
                    subelement_button_placeholder.empty()
                    chosen_subdir_placeholder.empty()
    else:
        state_placeholder.latex(state_failed)
        ret_state = state_failed
        sel_dict[key + "_chosen_subdir"] = None
        col6, col7 = st.columns([30, 70])
        reset_button_placeholder = col6.empty()
        error_placeholder = col7.empty()
        error_placeholder.error(f"The path {dirpath} is not a folder.")
        if reset_button_placeholder.button(
            "Reset to standard folder", key=key + "_reset_button", help=f"Reset folder to {local_save_path}"
        ):
            dirpath = dirpath_placeholder.text_input(
                label=label, value=local_save_path, key=key + "_text_input", help=help
            )
            state_placeholder.latex(state_ok)
            ret_state = state_ok
            error_placeholder.empty()
            reset_button_placeholder.empty()
            if parent_button_placeholder.button(
                "Go to parent directory", key=key + "_level_up", help="Go one directory up."
            ):
                pass
            subdirlist = [name for name in os.listdir(dirpath) if os.path.isdir(os.path.join(dirpath, name))]
            if len(subdirlist) > 0:
                if key + "_chosen_subdir" not in sel_dict.keys():
                    sel_dict[key + "_chosen_subdir"] = None
                sel_dict[key + "_chosen_subdir"] = chosen_subdir_placeholder.selectbox(
                    "Subdirectories:",
                    subdirlist,
                    subdirlist.index(sel_dict[key + "_chosen_subdir"])
                    if sel_dict[key + "_chosen_subdir"] and sel_dict[key + "_chosen_subdir"] in subdirlist
                    else 0,
                    key=key + "_chosen_subdir",
                )
                if subelement_button_placeholder.button(
                    "Go to subdirectory:", key=key + "_go_to", help="Go to the chosen subdirectory."
                ):
                    pass
        if ask_make and os.path.isdir(os.path.dirname(dirpath)):
            make_dir = st.button(f"Create dir: {dirpath}")
            if make_dir:
                os.makedirs(dirpath)
                subelement_button_placeholder.empty()
                chosen_subdir_placeholder.empty()
                reset_button_placeholder.empty()
                state_placeholder.latex(state_ok)
                ret_state = state_ok
                error_placeholder.empty()
                if parent_button_placeholder.button(
                    "Go to parent directory", key=key + "_level_up", help="Go one directory up."
                ):
                    dirpath = os.path.dirname(dirpath)
                    sel_dict[key + "_chosen_subdir"] = None
                    dirpath = dirpath_placeholder.text_input(
                        label=label, value=dirpath, key=key + "_text_input", help=help
                    )
    if return_state:
        return dirpath, ret_state
    return dirpath


def small_file_selector_old(label=None, value=local_save_path, key="", help=None, return_state=False):
    sel_dict = get_sel_dict()
    col1, col2 = st.columns([10, 1])
    col3, col4, col5 = st.columns([25, 25, 50])
    filepath_placeholder = col1.empty()
    state_placeholder = col2.empty()
    parent_button_placeholder = col3.empty()
    subelement_button_placeholder = col4.empty()
    chosen_subdir_placeholder = col5.empty()
    warning_placeholder = st.empty()
    filepath = filepath_placeholder.text_input(label=label, value=value, key=key + "_text_input", help=help)
    if filepath != value:
        filepath = filepath_placeholder.text_input(label=label, value=filepath, key=key + "_text_input", help=help)
    if os.path.isfile(filepath) or os.path.isdir(filepath):
        if os.path.isfile(filepath):
            state_placeholder.latex(state_ok)
            ret_state = state_ok
        else:
            state_placeholder.latex(state_uncertain)
            ret_state = state_uncertain
            warning_placeholder.warning("You have currently chosen a folder, but you have to choose a file here.")
        if parent_button_placeholder.button(
            "Go to parent directory", key=key + "_level_up", help="Go one directory up."
        ):
            filepath = os.path.dirname(filepath)
            sel_dict[key + "_chosen_subdir"] = None
            filepath = filepath_placeholder.text_input(label=label, value=filepath, key=key + "_text_input", help=help)
            warning_placeholder.warning("You have currently chosen a folder, but you have to choose a file here.")
            state_placeholder.latex(state_uncertain)
            ret_state = state_uncertain
        if os.path.isdir(filepath):
            subdirlist = os.listdir(filepath)
            if len(subdirlist) > 0:
                if key + "_chosen_subdir" not in sel_dict.keys():
                    sel_dict[key + "_chosen_subdir"] = None
                sel_dict[key + "_chosen_subdir"] = chosen_subdir_placeholder.selectbox(
                    "Subelements:",
                    subdirlist,
                    subdirlist.index(sel_dict[key + "_chosen_subdir"])
                    if sel_dict[key + "_chosen_subdir"] and sel_dict[key + "_chosen_subdir"] in subdirlist
                    else 0,
                )
                if subelement_button_placeholder.button(
                    "Go to subelement:", key=key + "_go_to", help="Go to the chosen subelement."
                ):
                    filepath = os.path.join(filepath, sel_dict[key + "_chosen_subdir"])
                    sel_dict[key + "_chosen_subdir"] = None
                    filepath = filepath_placeholder.text_input(
                        label=label, value=filepath, key=key + "_text_input", help=help
                    )
                    if os.path.isdir(filepath):
                        subdirlist = os.listdir(filepath)
                        if len(subdirlist) > 0:
                            sel_dict[key + "_chosen_subdir"] = chosen_subdir_placeholder.selectbox(
                                "Subelements:",
                                subdirlist,
                                subdirlist.index(sel_dict[key + "_chosen_subdir"])
                                if sel_dict[key + "_chosen_subdir"] and sel_dict[key + "_chosen_subdir"] in subdirlist
                                else 0,
                            )
                        else:
                            subelement_button_placeholder.empty()
                            chosen_subdir_placeholder.empty()
                    elif os.path.isfile(filepath):
                        subelement_button_placeholder.empty()
                        chosen_subdir_placeholder.empty()
                        warning_placeholder.empty()
                        state_placeholder.latex(state_ok)
                        ret_state = state_ok
    else:
        state_placeholder.latex(state_failed)
        ret_state = state_failed
        sel_dict[key + "_chosen_subdir"] = None
        col6, col7 = st.columns([30, 70])
        reset_button_placeholder = col6.empty()
        error_placeholder = col7.empty()
        error_placeholder.error(f"The path {filepath} is not a valid path.")

        if reset_button_placeholder.button(
            "Reset to standard folder", key=key + "_reset_button", help=f"Reset folder to {local_save_path}"
        ):
            filepath = filepath_placeholder.text_input(
                label=label, value=local_save_path, key=key + "_text_input", help=help
            )
            warning_placeholder.warning("You have currently chosen a folder, but you have to choose a file here.")
            state_placeholder.latex(state_uncertain)
            ret_state = state_uncertain
            error_placeholder.empty()
            reset_button_placeholder.empty()
            if parent_button_placeholder.button(
                "Go to parent directory", key=key + "_level_up", help="Go one directory up."
            ):
                pass
            if os.path.isdir(filepath):
                subdirlist = os.listdir(filepath)
                if len(subdirlist) > 0:
                    if key + "_chosen_subdir" not in sel_dict.keys():
                        sel_dict[key + "_chosen_subdir"] = None
                    sel_dict[key + "_chosen_subdir"] = chosen_subdir_placeholder.selectbox(
                        "Subelements:",
                        subdirlist,
                        subdirlist.index(sel_dict[key + "_chosen_subdir"])
                        if sel_dict[key + "_chosen_subdir"] and sel_dict[key + "_chosen_subdir"] in subdirlist
                        else 0,
                    )
                    if subelement_button_placeholder.button(
                        "Go to subelement:", key=key + "_go_to", help="Go to the chosen subelement."
                    ):
                        filepath = os.path.join(filepath, sel_dict[key + "_chosen_subdir"])
                        sel_dict[key + "_chosen_subdir"] = None
                        filepath = filepath_placeholder.text_input(
                            label=label, value=filepath, key=key + "_text_input", help=help
                        )
                        pass

    if return_state:
        return filepath, ret_state
    return filepath

def small_file_selector(label=None, value=local_save_path, key="", help=None, return_state=False):
    col1, col2 = st.columns([10, 1])
    col3, col4, col5 = st.columns([25, 25, 50])
    def fs_level_up():
        st.session_state[key] = os.path.dirname(st.session_state[key])
    def fs_goto():
        st.session_state[key] = os.path.join(st.session_state[key], st.session_state[key+'cur_subdir'])
        del st.session_state[key+'cur_subdir']
    def fs_reset():
        st.session_state[key] = local_save_path

    if key in st.session_state:
        col1.text_input(label=label, key=key, help=help)
    else:
        col1.text_input(label=label, value=value, key=key, help=help)
    if os.path.isfile(st.session_state[key]) or os.path.isdir(st.session_state[key]):
        if os.path.isfile(st.session_state[key]):
            col2.latex(state_ok)
            ret_state = state_ok
        else:
            col2.latex(state_uncertain)
            ret_state = state_uncertain
            st.warning("You have currently chosen a folder, but you have to choose a file here.")
        col3.button("Go to parent directory", key=key + "_level_up", help="Go one directory up.",on_click=fs_level_up)
        if os.path.isdir(st.session_state[key]):
            st.session_state[key+'subdirlist'] = os.listdir(st.session_state[key])
            if len(st.session_state[key+'subdirlist']) > 0:
                if key+'cur_subdir' in st.session_state and st.session_state[key+'cur_subdir'] not in st.session_state[key+'subdirlist']:
                    del st.session_state[key+'cur_subdir']
                col5.selectbox(
                    label="Subelements:",
                    options=st.session_state[key+'subdirlist'],
                    key=key+'cur_subdir'
                )
                col4.button("Go to subelement:", key=key + "_go_to", help="Go to the chosen subelement.",on_click=fs_goto)
    else:
        col2.latex(state_failed)
        ret_state = state_failed
        col6, col7 = st.columns([30, 70])
        col7.error(f"The path {st.session_state[key]} is not a valid path.")
        col6.button("Reset to standard folder", key=key + "_reset_button", help=f"Reset folder to {local_save_path}",on_click=fs_reset)


    if return_state:
        return st.session_state[key], ret_state
    return st.session_state[key]


def selectbox_widget(label, options, index=0, format_func=str, key=None, help=None, st_element=st):
    # Use this workaround because streamlit sometimes jumps in the GUI back to the original value after a change of the value of a selectbox.
    #sel_box_placeholder = st_element.empty()
    #ret_value = sel_box_placeholder.selectbox(
    #    label=label, options=options, index=index, format_func=format_func, key=key, help=help
    #)
    #if options.index(ret_value) != index:
    #    ret_value = sel_box_placeholder.selectbox(
    #        label=label, options=options, index=options.index(ret_value), format_func=format_func, key=key, help=help
    #    )
    #return ret_value
    return st_element.selectbox(
        label=label, options=options, index=index, format_func=format_func, key=key, help=help
    )


def radio_widget(label, options, index=0, format_func=str, key=None, help=None, st_element=st):
    # Use this workaround because streamlit sometimes jumps in the GUI back to the original value after a change of the value of a radio button.
    #radio_placeholder = st_element.empty()
    #ret_value = radio_placeholder.radio(
    #    label=label, options=options, index=index, format_func=format_func, key=key, help=help
    #)
    #if options.index(ret_value) != index:
    #    radio_placeholder.radio(
    #        label=label, options=options, index=options.index(ret_value), format_func=format_func, key=key, help=help
    #    )
    #return ret_value
    return st_element.radio(
        label=label, options=options, index=index, format_func=format_func, key=key, help=help
    )


def text_input_widget(label, value="", max_chars=None, key=None, type="default", help=None, st_element=st):
    # Use this workaround because streamlit sometimes jumps in the GUI back to the original value after a change of the value of text input.
    #text_input_placeholder = st_element.empty()
    #ret_value = text_input_placeholder.text_input(
    #    label, value=value, max_chars=max_chars, key=key, type=type, help=help
    #)
    #if value != ret_value:
    #    ret_value = text_input_placeholder.text_input(
    #        label, value=ret_value, max_chars=max_chars, key=key, type=type, help=help
    #    )
    #return ret_value
    return st_element.text_input(
        label, value=value, max_chars=max_chars, key=key, type=type, help=help
    )

def checkbox_widget(label, value=False, key=None, help=None, st_element=st):
    # Use this workaround because streamlit sometimes jumps in the GUI back to the original value after a change of the value of a checkbox.
    #checkbox_placeholder = st_element.empty()
    #ret_value = checkbox_placeholder.checkbox(
    #    label, value=value, key=key, help=help
    #)
    #if value != ret_value:
    #    ret_value = checkbox_placeholder.checkbox(
    #        label, value=ret_value, key=key, help=help
    #    )
    #return ret_value
    return st_element.checkbox(
        label, value=value, key=key, help=help
    )

def number_input_widget(
        label,
        min_value=None,
        max_value=None,
        value=None,
        step=None,
        format=None,
        key=None,
        help=None,
        st_element=st,
    ):
    # Use this workaround because streamlit sometimes jumps in the GUI back to the original value after a change of the value of a number_input.
    #number_input_placeholder=st_element.empty()

    #ret_value=number_input_placeholder.number_input(label=label,
    #    min_value=min_value,
    #    max_value=max_value,
    #    value=value,
    #    step=step,
    #    format=format,
    #    key=key,
    #    help=help)
    #if value != ret_value:
    #    ret_value=number_input_placeholder.number_input(label=label,
    #        min_value=min_value,
    #        max_value=max_value,
    #        value=ret_value,
    #        step=step,
    #        format=format,
    #        key=key,
    #        help=help)
    #return ret_value
    return st_element.number_input(label=label,
        min_value=min_value,
        max_value=max_value,
        value=value,
        step=step,
        format=format,
        key=key,
        help=help)
