import streamlit as st
import json
import os
import random
import math
import shutil

from tei_entity_enricher.util.helper import (
    module_path,
    local_save_path,
    makedir_if_necessary,
)
import tei_entity_enricher.menu.tei_ner_map as tei_map
import tei_entity_enricher.menu.tei_reader as tei_reader
import tei_entity_enricher.menu.ner_task_def as ner_task
import tei_entity_enricher.util.tei_parser as tp
from tei_entity_enricher.util.spacy_lm import lang_dict, get_spacy_lm
from tei_entity_enricher.util.components import (
    small_dir_selector,
    text_input_widget,
    selectbox_widget,
    radio_widget,
    number_input_widget,
)
from dataclasses import dataclass
from dataclasses_json import dataclass_json

# from tei_entity_enricher.menu.tei_postprocessing import get_entity_library


@dataclass
@dataclass_json
class TEINERGBParams:
    tng_name: str = None
    tng_lang: str = None
    tng_tr_name: str = None
    tng_tnm_name: str = None
    tng_test_percentage: int = None
    tng_dev_percentage: int = None
    tng_shuffle_options: str = None
    tng_teifile_folder: str = None
    tng_del_gt_name: str = None
    tng_selected_display_tng_name: str = None


@st.cache(allow_output_mutation=True)
def get_params() -> TEINERGBParams:
    return TEINERGBParams()


class TEINERGroundtruthBuilder:
    def __init__(self, state, show_menu=True):
        self.tng_Folder = "TNG"
        self.template_tng_Folder = os.path.join(module_path, "templates", self.tng_Folder)
        self.tng_Folder = os.path.join(local_save_path, self.tng_Folder)
        self.tng_attr_name = "name"
        self.tng_attr_tr = "tr"
        self.tng_attr_tnm = "tnm"
        self.tng_attr_lang = "lang"
        self.tng_attr_ratio = "ratio"
        self.tng_attr_shuffle_type = "shuffle_type"
        self.tng_attr_template = "template"
        self.tng_gt_type_train = "train"
        self.tng_gt_type_dev = "dev"
        self.tng_gt_type_test = "test"

        self.shuffle_options_dict = {
            "Shuffle by TEI File": True,
            "Shuffle by Sentences": False,
        }

        makedir_if_necessary(self.tng_Folder)
        makedir_if_necessary(self.template_tng_Folder)

        self.refresh_tng_list()

        if show_menu:
            self.tnm = tei_map.TEINERMap(state, show_menu=False)
            self.tr = tei_reader.TEIReader(state, show_menu=False)
            self.ntd = ner_task.NERTaskDef(state, show_menu=False)
            self.show()

    @property
    def tei_ner_gb_params(self) -> TEINERGBParams:
        return get_params()

    def refresh_tng_list(self):
        self.tnglist = []
        for gt_folder in sorted(os.listdir(self.template_tng_Folder)):
            if os.path.isdir(os.path.join(self.template_tng_Folder, gt_folder)) and os.path.isfile(
                os.path.join(self.template_tng_Folder, gt_folder, os.path.basename(gt_folder) + ".json")
            ):
                with open(
                    os.path.join(
                        self.template_tng_Folder,
                        gt_folder,
                        os.path.basename(gt_folder) + ".json",
                    )
                ) as f:
                    self.tnglist.append(json.load(f))
        for gt_folder in sorted(os.listdir(self.tng_Folder)):
            if os.path.isdir(os.path.join(self.tng_Folder, gt_folder)) and os.path.isfile(
                os.path.join(self.tng_Folder, gt_folder, os.path.basename(gt_folder) + ".json")
            ):
                with open(
                    os.path.join(
                        self.tng_Folder,
                        gt_folder,
                        os.path.basename(gt_folder) + ".json",
                    )
                ) as f:
                    self.tnglist.append(json.load(f))

        self.tngdict = {}
        self.editable_tng_names = []
        for tng in self.tnglist:
            self.tngdict[tng[self.tng_attr_name]] = tng
            if not tng[self.tng_attr_template]:
                self.editable_tng_names.append(tng[self.tng_attr_name])

    def validate_build_configuration(self, build_config, folder_path):
        val = True
        if (
            self.tng_attr_name not in build_config.keys()
            or build_config[self.tng_attr_name] is None
            or build_config[self.tng_attr_name] == ""
        ):
            val = False
            st.error("Please define a name for the Groundtruth before building it!")
        elif os.path.isdir(os.path.join(self.tng_Folder, build_config[self.tng_attr_name].replace(" ", "_"))):
            val = False
            st.error(
                f"Choose another name. There is already a Groundtruth with name {build_config[self.tng_attr_name]}!"
            )
        if folder_path is None or folder_path == "":
            val = False
            st.error(f"Please choose a folder containing the TEI-Files you want to use to build the groundtruth from!")
        elif not os.path.isdir(folder_path):
            val = False
            st.error(f"The directory {folder_path} doesn't exist. Please choose valid directory!")
        return val

    def build_groundtruth(self, build_config, folder_path):
        build_config[self.tng_attr_template] = False
        progressoutput = st.success("Prepare Groundtruth building...")
        save_folder = os.path.join(self.tng_Folder, build_config[self.tng_attr_name].replace(" ", "_"))
        makedir_if_necessary(save_folder)
        save_test_folder = os.path.join(save_folder, self.tng_gt_type_test)
        makedir_if_necessary(save_test_folder)
        save_dev_folder = os.path.join(save_folder, self.tng_gt_type_dev)
        makedir_if_necessary(save_dev_folder)
        save_train_folder = os.path.join(save_folder, self.tng_gt_type_train)
        makedir_if_necessary(save_train_folder)

        nlp = get_spacy_lm(build_config[self.tng_attr_lang])
        by_file = self.shuffle_options_dict[build_config[self.tng_attr_shuffle_type]]
        filelist = os.listdir(folder_path)
        if not by_file:
            all_data = []
        else:
            random.shuffle(filelist)

        build_gb_progress_bar = st.progress(0)
        trainfilelist = []
        devfilelist = []
        testfilelist = []
        for fileindex in range(len(filelist)):
            if filelist[fileindex].endswith(".xml"):
                progressoutput.success(f"Process file {filelist[fileindex]}...")
                brief = tp.TEIFile(
                    os.path.join(folder_path, filelist[fileindex]),
                    build_config[self.tng_attr_tr],
                    entity_dict=build_config[self.tng_attr_tnm][self.tnm.tnm_attr_entity_dict],
                    nlp=nlp,
                    with_position_tags=True,
                )
                raw_ner_data = tp.split_into_sentences(brief.build_tagged_text_line_list())
                if not by_file:
                    all_data.extend(raw_ner_data)
                else:
                    if fileindex <= (build_config[self.tng_attr_ratio][self.tng_gt_type_test] / 100.0) * len(filelist):
                        testfilepath = os.path.join(save_test_folder, filelist[fileindex] + ".json")
                        testfilelist.append(testfilepath + "\n")
                        with open(
                            testfilepath,
                            "w+",
                        ) as g:
                            json.dump(raw_ner_data, g)
                    elif fileindex <= (
                        (
                            build_config[self.tng_attr_ratio][self.tng_gt_type_test]
                            + build_config[self.tng_attr_ratio][self.tng_gt_type_dev]
                        )
                        / 100.0
                    ) * len(filelist):
                        devfilepath = os.path.join(save_dev_folder, filelist[fileindex] + ".json")
                        devfilelist.append(devfilepath + "\n")
                        with open(
                            devfilepath,
                            "w+",
                        ) as g:
                            json.dump(raw_ner_data, g)
                    else:
                        trainfilepath = os.path.join(save_train_folder, filelist[fileindex] + ".json")
                        trainfilelist.append(trainfilepath + "\n")
                        with open(
                            trainfilepath,
                            "w+",
                        ) as g:
                            json.dump(raw_ner_data, g)
            build_gb_progress_bar.progress(math.floor((fileindex + 1) / len(filelist) * 100))
        if not by_file:
            progressoutput.success("Shuffle and save the data...")
            random.shuffle(all_data)
            test_list = []
            dev_list = []
            train_list = []
            for data_index in range(len(all_data)):
                if data_index <= (build_config[self.tng_attr_ratio][self.tng_gt_type_test] / 100.0) * len(all_data):
                    test_list.append(all_data[data_index])
                elif data_index <= (
                    (
                        build_config[self.tng_attr_ratio][self.tng_gt_type_test]
                        + build_config[self.tng_attr_ratio][self.tng_gt_type_dev]
                    )
                    / 100.0
                ) * len(all_data):
                    dev_list.append(all_data[data_index])
                else:
                    train_list.append(all_data[data_index])
            testfilepath = os.path.join(
                save_test_folder,
                self.tng_gt_type_test + "_" + build_config[self.tng_attr_name].replace(" ", "_") + ".json",
            )
            testfilelist.append(testfilepath + "\n")
            with open(
                testfilepath,
                "w+",
            ) as g:
                json.dump(test_list, g)
            devfilepath = os.path.join(
                save_dev_folder,
                self.tng_gt_type_dev + "_" + build_config[self.tng_attr_name].replace(" ", "_") + ".json",
            )
            devfilelist.append(devfilepath + "\n")
            with open(
                devfilepath,
                "w+",
            ) as g2:
                json.dump(dev_list, g2)
            trainfilepath = os.path.join(
                save_train_folder,
                self.tng_gt_type_train + "_" + build_config[self.tng_attr_name].replace(" ", "_") + ".json",
            )
            trainfilelist.append(trainfilepath + "\n")
            with open(
                trainfilepath,
                "w+",
            ) as h:
                json.dump(train_list, h)
        with open(
            os.path.join(
                save_folder,
                build_config[self.tng_attr_name].replace(" ", "_") + ".json",
            ),
            "w+",
        ) as h2:
            json.dump(build_config, h2)
        with open(
            os.path.join(
                save_folder,
                self.tng_gt_type_test + "_" + build_config[self.tng_attr_name].replace(" ", "_") + ".lst",
            ),
            "w+",
        ) as htest:
            htest.writelines(testfilelist)
        with open(
            os.path.join(
                save_folder,
                self.tng_gt_type_dev + "_" + build_config[self.tng_attr_name].replace(" ", "_") + ".lst",
            ),
            "w+",
        ) as hdev:
            hdev.writelines(devfilelist)
        with open(
            os.path.join(
                save_folder,
                self.tng_gt_type_train + "_" + build_config[self.tng_attr_name].replace(" ", "_") + ".lst",
            ),
            "w+",
        ) as htrain:
            htrain.writelines(trainfilelist)
        progressoutput.success(f"Groundtruth {build_config[self.tng_attr_name]} succesfully builded.")
        st.write(f"Statistics for {build_config[self.tng_attr_name]}")
        self.show_statistics_to_saved_groundtruth(
            save_folder,
            build_config[self.tng_attr_tnm][self.tnm.tnm_attr_ntd][self.ntd.ntd_attr_entitylist],
        )
        self.refresh_tng_list()

    def build_tng_stats_tablestring(self, entity_list, train_stats, dev_stats, test_stats):
        tablestring = "Entity | \# All | \# Train | \# Test | \# Devel \n -----|-------|-------|-------|-------"
        for entity in entity_list:
            train_num = train_stats["B-" + entity] if "B-" + entity in train_stats.keys() else 0
            test_num = test_stats["B-" + entity] if "B-" + entity in test_stats.keys() else 0
            dev_num = dev_stats["B-" + entity] if "B-" + entity in dev_stats.keys() else 0
            tablestring += (
                "\n "
                + entity
                + " | "
                + str(train_num + test_num + dev_num)
                + " | "
                + str(train_num)
                + " | "
                + str(test_num)
                + " | "
                + str(dev_num)
            )
        train_num = train_stats["O"] if "O" in train_stats.keys() else 0
        test_num = test_stats["O"] if "O" in test_stats.keys() else 0
        dev_num = dev_stats["O"] if "O" in dev_stats.keys() else 0
        tablestring += (
            "\n "
            + "unlabeled words"
            + " | "
            + str(train_num + test_num + dev_num)
            + " | "
            + str(train_num)
            + " | "
            + str(test_num)
            + " | "
            + str(dev_num)
        )
        return tablestring

    def build_ner_statistics(self, directory):
        tag_collect = {}
        for filename in os.listdir(directory):
            if filename.endswith(".json"):
                with open(os.path.join(directory, filename)) as f:
                    training_data = json.load(f)
                for i in range(len(training_data)):
                    for j in range(len(training_data[i])):
                        if training_data[i][j][1] in tag_collect.keys():
                            tag_collect[training_data[i][j][1]] += 1
                        else:
                            tag_collect[training_data[i][j][1]] = 1
        return {k: v for k, v in sorted(tag_collect.items(), key=lambda item: item[1])}

    def show_statistics_to_saved_groundtruth(self, directory, entity_list):
        test_folder = os.path.join(directory, self.tng_gt_type_test)
        dev_folder = os.path.join(directory, self.tng_gt_type_dev)
        train_folder = os.path.join(directory, self.tng_gt_type_train)
        st.markdown(
            self.build_tng_stats_tablestring(
                entity_list,
                self.build_ner_statistics(train_folder),
                self.build_ner_statistics(dev_folder),
                self.build_ner_statistics(test_folder),
            ),
            unsafe_allow_html=True,
        )
        st.markdown(" ")  # only for layouting reasons (placeholder)

    def show_build_gt_environment(self):
        tng_dict = {}
        col1, col2 = st.beta_columns(2)
        with col1:
            self.tei_ner_gb_params.tng_name = text_input_widget(
                "Define a name for the groundtruth:", self.tei_ner_gb_params.tng_name or ""
            )
            if self.tei_ner_gb_params.tng_name:
                tng_dict[self.tng_attr_name] = self.tei_ner_gb_params.tng_name
            self.tei_ner_gb_params.tng_lang = selectbox_widget(
                "Select a language for the groundtruth (relevant for the split into sentences):",
                list(lang_dict.keys()),
                list(lang_dict.keys()).index(self.tei_ner_gb_params.tng_lang) if self.tei_ner_gb_params.tng_lang else 0,
                key="tng_lang",
            )
            if self.tei_ner_gb_params.tng_lang:
                tng_dict[self.tng_attr_lang] = self.tei_ner_gb_params.tng_lang
        with col2:
            self.tei_ner_gb_params.tng_tr_name = selectbox_widget(
                "Select a TEI Reader Config for Building the groundtruth:",
                list(self.tr.configdict.keys()),
                list(self.tr.configdict.keys()).index(self.tei_ner_gb_params.tng_tr_name)
                if self.tei_ner_gb_params.tng_tr_name
                else 0,
                key="tng_tr",
            )
            if self.tei_ner_gb_params.tng_tr_name:
                tng_dict[self.tng_attr_tr] = self.tr.configdict[self.tei_ner_gb_params.tng_tr_name]
            self.tei_ner_gb_params.tng_tnm_name = selectbox_widget(
                "Select a TEI Read NER Entity Mapping for Building the groundtruth:",
                list(self.tnm.mappingdict.keys()),
                list(self.tnm.mappingdict.keys()).index(self.tei_ner_gb_params.tng_tnm_name)
                if self.tei_ner_gb_params.tng_tnm_name
                else 0,
                key="tng_tnm",
            )
            if self.tei_ner_gb_params.tng_tnm_name:
                tng_dict[self.tng_attr_tnm] = self.tnm.mappingdict[self.tei_ner_gb_params.tng_tnm_name]

        col3, col4 = st.beta_columns(2)
        col5, col6, col7 = st.beta_columns([0.25, 0.25, 0.5])
        with col3:
            st.markdown("Define a ratio for the partition into train- development- and testset.")
        with col5:
            self.tei_ner_gb_params.tng_test_percentage = number_input_widget(
                "Percentage for the test set",
                min_value=0,
                max_value=100
                - (self.tei_ner_gb_params.tng_dev_percentage if self.tei_ner_gb_params.tng_dev_percentage else 10),
                value=self.tei_ner_gb_params.tng_test_percentage if self.tei_ner_gb_params.tng_test_percentage else 10,
            )
        with col6:
            self.tei_ner_gb_params.tng_dev_percentage = number_input_widget(
                "Percentage for the validation set",
                min_value=0,
                max_value=100
                - (self.tei_ner_gb_params.tng_test_percentage if self.tei_ner_gb_params.tng_test_percentage else 10),
                value=self.tei_ner_gb_params.tng_dev_percentage if self.tei_ner_gb_params.tng_dev_percentage else 10,
            )
        with col7:
            self.tei_ner_gb_params.tng_shuffle_options = radio_widget(
                "Shuffle Options",
                tuple(self.shuffle_options_dict.keys()),
                tuple(self.shuffle_options_dict.keys()).index(self.tei_ner_gb_params.tng_shuffle_options)
                if self.tei_ner_gb_params.tng_shuffle_options
                else 0,
            )
            tng_dict[self.tng_attr_shuffle_type] = self.tei_ner_gb_params.tng_shuffle_options
        col8, col9 = st.beta_columns(2)
        with col8:
            st.write(
                "With this configuration you have ",
                100 - self.tei_ner_gb_params.tng_dev_percentage - self.tei_ner_gb_params.tng_test_percentage,
                "% of the data for the train set, ",
                self.tei_ner_gb_params.tng_dev_percentage,
                "% for the development set and",
                self.tei_ner_gb_params.tng_test_percentage,
                "% for the test set.",
            )
        self.tei_ner_gb_params.tng_teifile_folder = small_dir_selector(
            label="Choose a Folder containing only TEI Files to build the groundtruth from:",
            value=self.tei_ner_gb_params.tng_teifile_folder
            if self.tei_ner_gb_params.tng_teifile_folder
            else local_save_path,
            key="tng_tei_file_folder",
        )
        tng_dict[self.tng_attr_ratio] = {
            self.tng_gt_type_train: 100
            - self.tei_ner_gb_params.tng_dev_percentage
            - self.tei_ner_gb_params.tng_test_percentage,
            self.tng_gt_type_dev: self.tei_ner_gb_params.tng_dev_percentage,
            self.tng_gt_type_test: self.tei_ner_gb_params.tng_test_percentage,
        }
        if st.button("Build Groundtruth"):
            if self.validate_build_configuration(tng_dict, self.tei_ner_gb_params.tng_teifile_folder):
                self.build_groundtruth(tng_dict, self.tei_ner_gb_params.tng_teifile_folder)

    def delete_groundtruth(self, groundtruth):
        val = True
        if val:
            shutil.rmtree(os.path.join(self.tng_Folder, groundtruth[self.tng_attr_name].replace(" ", "_")))
            if self.tei_ner_gb_params.tng_selected_display_tng_name == groundtruth[self.tng_attr_name]:
                self.tei_ner_gb_params.tng_selected_display_tng_name = None
            self.tei_ner_gb_params.tng_del_gt_name = None
            st.experimental_rerun()

    def show_del_environment(self):
        if len(self.editable_tng_names) > 0:
            self.tei_ner_gb_params.tng_del_gt_name = selectbox_widget(
                "Select a groundtruth to delete!",
                self.editable_tng_names,
                index=self.editable_tng_names.index(self.tei_ner_gb_params.tng_del_gt_name)
                if self.tei_ner_gb_params.tng_del_gt_name
                else 0,
            )
            if st.button("Delete Selected Groundtruth"):
                self.delete_groundtruth(self.tngdict[self.tei_ner_gb_params.tng_del_gt_name])
        else:
            st.info("There is no self-defined Groundtruth to delete!")

    def build_tng_tablestring(self):
        tablestring = "Name | TEI Reader Config | TEI Read NER Entity Mapping | Language | Shuffle Type | Partition Ratio | Template \n -----|-------|-------|-------|-------|-------|-------"
        for tng in self.tnglist:
            if tng[self.tng_attr_template]:
                template = "yes"
            else:
                template = "no"
            if self.shuffle_options_dict[tng[self.tng_attr_shuffle_type]]:
                shuffle_type = "by file"
            else:
                shuffle_type = "by sentences"
            partition_ratio = f"Train: {tng[self.tng_attr_ratio][self.tng_gt_type_train]}%, Test: {tng[self.tng_attr_ratio][self.tng_gt_type_test]}%, Devel: {tng[self.tng_attr_ratio][self.tng_gt_type_dev]}%"
            tablestring += (
                "\n "
                + tng[self.tng_attr_name]
                + " | "
                + tng[self.tng_attr_tr][self.tr.tr_config_attr_name]
                + " | "
                + tng[self.tng_attr_tnm][self.tnm.tnm_attr_name]
                + " | "
                + tng[self.tng_attr_lang]
                + " | "
                + shuffle_type
                + " | "
                + partition_ratio
                + " | "
                + template
            )
        return tablestring

    def show_existing_tng(self):
        st.markdown(self.build_tng_tablestring())
        st.markdown(" ")  # only for layouting reasons (placeholder)
        self.tei_ner_gb_params.tng_selected_display_tng_name = selectbox_widget(
            f"Choose a groundtruth for displaying its statistics:",
            list(self.tngdict.keys()),
            list(self.tngdict.keys()).index(self.tei_ner_gb_params.tng_selected_display_tng_name)
            if self.tei_ner_gb_params.tng_selected_display_tng_name
            else 0,
            key="tng_stats",
        )
        if self.tei_ner_gb_params.tng_selected_display_tng_name:
            cur_sel_tng = self.tngdict[self.tei_ner_gb_params.tng_selected_display_tng_name]
            if cur_sel_tng[self.tng_attr_template]:
                cur_folder = self.template_tng_Folder
            else:
                cur_folder = self.tng_Folder
            self.show_statistics_to_saved_groundtruth(
                os.path.join(cur_folder, cur_sel_tng[self.tng_attr_name].replace(" ", "_")),
                cur_sel_tng[self.tng_attr_tnm][self.tnm.tnm_attr_ntd][self.ntd.ntd_attr_entitylist],
            )

    def show(self):
        st.latex("\\text{\Huge{TEI NER Groundtruth Builder}}")
        tng_build_new = st.beta_expander("Build new TEI NER Groundtruth", expanded=False)
        with tng_build_new:
            self.show_build_gt_environment()
        tng_delete = st.beta_expander("Delete existing TEI NER Groundtruth", expanded=False)
        with tng_delete:
            self.show_del_environment()
        tng_show = st.beta_expander("Show existing TEI NER Groundtruth", expanded=True)
        with tng_show:
            self.show_existing_tng()

    def get_filepath_to_gt_lists(self, name):
        save_folder = os.path.join(self.tng_Folder, name.replace(" ", "_"))
        makedir_if_necessary(save_folder)
        testlistfilepath = os.path.join(
            save_folder,
            self.tng_gt_type_test + "_" + name.replace(" ", "_") + ".lst",
        )
        devlistfilepath = os.path.join(
            save_folder,
            self.tng_gt_type_dev + "_" + name.replace(" ", "_") + ".lst",
        )
        trainlistfilepath = os.path.join(
            save_folder,
            self.tng_gt_type_train + "_" + name.replace(" ", "_") + ".lst",
        )
        if self.tngdict[name][self.tng_attr_template]:
            if not (
                os.path.isfile(trainlistfilepath)
                and os.path.isfile(devlistfilepath)
                and os.path.isfile(testlistfilepath)
            ):
                templ_folder = os.path.join(self.template_tng_Folder, name.replace(" ", "_"))
                save_test_folder = os.path.join(templ_folder, self.tng_gt_type_test)
                save_dev_folder = os.path.join(templ_folder, self.tng_gt_type_dev)
                save_train_folder = os.path.join(templ_folder, self.tng_gt_type_train)
                testfilelist = [
                    os.path.join(save_test_folder, filepath + "\n")
                    for filepath in os.listdir(save_test_folder)
                    if filepath.endswith(".json")
                ]
                devfilelist = [
                    os.path.join(save_dev_folder, filepath + "\n")
                    for filepath in os.listdir(save_dev_folder)
                    if filepath.endswith(".json")
                ]
                trainfilelist = [
                    os.path.join(save_train_folder, filepath + "\n")
                    for filepath in os.listdir(save_train_folder)
                    if filepath.endswith(".json")
                ]
                with open(
                    os.path.join(
                        save_folder,
                        testlistfilepath,
                    ),
                    "w+",
                ) as htest:
                    htest.writelines(testfilelist)
                with open(
                    os.path.join(
                        save_folder,
                        devlistfilepath,
                    ),
                    "w+",
                ) as hdev:
                    hdev.writelines(devfilelist)
                with open(
                    os.path.join(
                        save_folder,
                        trainlistfilepath,
                    ),
                    "w+",
                ) as htrain:
                    htrain.writelines(trainfilelist)
        return trainlistfilepath, devlistfilepath, testlistfilepath
