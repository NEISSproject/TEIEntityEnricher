import os

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid


def editable_single_column_table(entry_list, key, head, openentrys=100, height=150, width=1):
    response = AgGrid(
        pd.DataFrame({head: entry_list + [""] * openentrys}),  # input_dataframe,
        height=height,
        editable=True,
        sortable=False,
        filter=False,
        resizable=True,
        defaultWidth=width,
        fit_columns_on_grid_load=True,
        key=key,
    )
    st.info("Edit the table by double-click in it and press Enter after changing a cell.")
    returnlist = []
    if "data" in response:
        all_list = list(response["data"].to_dict()[head].values())
        for element in all_list:
            if element != "" and element is not None:
                returnlist.append(element)
    return returnlist


def editable_multi_column_table(entry_dict, key, openentrys=100, height=150, width=1):
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
    with st.beta_expander(target, expanded=False):
        selected_file = file_selector(folder_path, parent=target, init_file=init_file)
    return selected_file


def dir_selector_expander(folder_path="", target="Select directory..."):
    with st.beta_expander(target):
        selected_dir = dir_selector(folder_path, parent=target)
    return selected_dir


def file_selector(folder_path="", sub_level=0, max_level=10, parent="", init_file=""):
    filenames = [
        f for f in os.listdir(os.path.join(os.getcwd(), folder_path)) if not f[0] == "."
    ]  # get file names from dir excluding hidden files
    a, b = st.beta_columns([sub_level + 1, 2 * max_level])
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
    a, b, c = st.beta_columns([sub_level + 1, 2 * max_level, 2])
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
