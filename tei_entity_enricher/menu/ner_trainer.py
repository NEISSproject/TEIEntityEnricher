import json
import logging
import os
import shutil

import streamlit as st
from streamlit_ace import st_ace

from tei_entity_enricher.util import config_io
from tei_entity_enricher.util.helper import (
    module_path,
    state_ok,
    state_failed,
    state_uncertain,
    file_lists_entry_widget,
    numbers_lists_entry_widget,
    model_dir_entry_widget,
    text_entry_with_check,
    check_dir_ask_make,
    remember_cwd,
)
from tei_entity_enricher.util.train_manager import get_manager

logger = logging.getLogger(__name__)


class NERTrainer(object):
    def __init__(
        self,
        state,
        show_menu=True,
    ):
        self._workdir_path = os.getcwd()
        self.state = state
        self.training_state = None
        self.trainer_params_json = None
        self.selected_train_list = None
        if self.workdir() != 0:
            return
        with remember_cwd():
            os.chdir(self._workdir_path)
            with st.beta_expander("Train configuration"):
                logger.info("load trainer params")
                if self.load_trainer_params() != 0:
                    st.error("Failed to load trainer_params.json")
                    return
                if self.data_configuration() != 0:
                    st.error("Failed to run data_configuration")
                    return
            # assert len(self.trainer_params_json["gen"]["train"]["lists"]) == 1, "Only one list is supported!"
            # self.trainer_params_json["gen"]["train"]["lists"][0] = file_selector_expander(
            #     target=f'train.lists: {self.trainer_params_json["gen"]["train"]["lists"][0]}',
            #     init_file=self.trainer_params_json["gen"]["train"]["lists"][0],
            # )
            if st.button(f'Save trainer_params to config: {os.path.join(self._workdir_path, "trainer_params.json")}'):
                with open(os.path.join(self._workdir_path, "trainer_params.json"), "w") as fp_tp:
                    json.dump(self.trainer_params_json, fp_tp)
                logger.info(f'trainer params saved to: {os.path.join(self._workdir_path, "trainer_params.json")}')
                st.experimental_rerun()

            # Manage Training Process
            # if not self.prelaunch_check():
            #     return
            train_manager = get_manager(workdir=self._workdir_path)
            st.text("Train Manager")
            if st.button("Set trainer params"):
                train_manager.set_params(self.trainer_params_json)
                logger.info("trainer params set!")
            b1, b2, b3, b4 = st.beta_columns(4)
            if b1.button("Start"):
                train_manager.start()
            if b2.button("Stop"):
                train_manager.stop()
            if b3.button("Clear"):
                train_manager.clear_process()
            if b4.button("refresh"):
                logger.info("refresh streamlit")

            if train_manager.has_process():
                with st.beta_expander("Epoch progress", expanded=True):
                    progress_str = train_manager.read_progress()
                    logger.info(progress_str)
                    st.text(progress_str)
            if train_manager.has_process():
                with st.beta_expander("Train log", expanded=True):
                    log_str = train_manager.log_content()
                    # logger.info(log_str)
                    # streamlit_ace.LANGUAGES
                    st_ace(
                        log_str,
                        language="powershell",
                        auto_update=True,
                        readonly=True,
                        height=300,
                        wrap=True,
                        font_size=12,
                    )
                    # st.text(log_str)
            # print(os.getcwd())
            # selected_file = file_selector_expander(folder_path=os.getcwd())
            # st.text(selected_file)
            # selected_dir = dir_selector_expander(folder_path=os.getcwd())
            # st.text(selected_dir)

    # def prelaunch_check(self):
    #     self.trainer_params_json

    def load_trainer_params(self):
        if not os.path.isfile("trainer_params.json"):
            logger.info("copy trainer_params.json from template")
            shutil.copy(
                os.path.join(module_path, "templates", "trainer", "trainer_params.json"),
                os.getcwd(),
            )
        if not os.path.isdir("templates"):
            logger.info("copy template_wd from templates")
            shutil.copytree(
                os.path.join(module_path, "templates", "trainer", "template_wd", "templates"),
                os.path.join(os.getcwd(), "templates"),
            )
        self.trainer_params_json = config_io.get_config("trainer_params.json")
        return 0

    def data_configuration(self):
        check_list = []

        train_lists = file_lists_entry_widget(
            self.trainer_params_json["gen"]["train"]["lists"],
            name="train.lists",
            help=", separated file names",
        )
        if train_lists:
            self.trainer_params_json["gen"]["train"]["lists"] = train_lists
            self.save_train_params()
        else:
            check_list.append("train.lists")
        if len(train_lists) > 1 or len(self.trainer_params_json["gen"]["train"]["list_ratios"]) > 1:
            train_lists_ratio = numbers_lists_entry_widget(
                self.trainer_params_json["gen"]["train"]["list_ratios"],
                name="train.list_ratios",
                expect_amount=len(train_lists),
                help="e.g. '1.0, 2.0' must be same amount as file names",
            )
            if train_lists_ratio:
                self.trainer_params_json["gen"]["train"]["list_ratios"] = train_lists_ratio
                self.save_train_params()
            else:
                check_list.append("train.list_ratios")
        val_lists = file_lists_entry_widget(
            self.trainer_params_json["gen"]["val"]["lists"],
            name="val.lists",
            help=", separated file names",
        )
        if val_lists:
            self.trainer_params_json["gen"]["val"]["lists"] = val_lists
            self.save_train_params()
        else:
            check_list.append("val.lists")
        if len(val_lists) > 1 or len(self.trainer_params_json["gen"]["val"]["list_ratios"]) > 1:
            val_lists_ratio = numbers_lists_entry_widget(
                self.trainer_params_json["gen"]["val"]["list_ratios"],
                name="val.list_ratios",
                expect_amount=len(val_lists),
                help="e.g. '1.0, 2.0' must be same amount as file names",
            )
            if val_lists_ratio:
                self.trainer_params_json["gen"]["val"]["list_ratios"] = val_lists_ratio
                self.save_train_params()
            else:
                check_list.append("val.list_ratios")

        pretrained_model = model_dir_entry_widget(
            self.trainer_params_json["scenario"]["model"]["pretrained_bert"],
            name="model.pretrained_bert",
            expect_saved_model=True,
        )
        if pretrained_model:
            self.trainer_params_json["scenario"]["model"]["pretrained_bert"] = pretrained_model
            self.save_train_params()
        else:
            check_list.append("model.pretrained_bert")
        #
        # output_dir = model_dir_entry_widget(self.trainer_params_json["output_dir"], name="output_dir")
        # if output_dir:
        #     self.trainer_params_json["output_dir"] = output_dir
        #     self.save_train_params()
        # else:
        #     check_list.append("output_dir")

        output_dir = text_entry_with_check(
            string=self.trainer_params_json["output_dir"],
            name="output_dir",
            check_fn=check_dir_ask_make,
        )
        if output_dir:
            self.trainer_params_json["output_dir"] = output_dir
            self.save_train_params()
        else:
            check_list.append("output_dir")

        if check_list:
            st.error(f"Fix {check_list} to continue!")
            logger.error(f"Fix {check_list} to continue!")
            return -1
        else:
            logger.info("data configuration successful")
            return 0

    def workdir(self):
        start_config_path = os.path.join(module_path, "templates", "trainer", "start_config.state")
        start_config = config_io.get_config(start_config_path)
        st_workdir_path, st_wdp_status = st.beta_columns([10, 1])

        if start_config and os.path.isdir(start_config["workdir"]):
            workdir_path = start_config["workdir"]
        else:
            workdir_path = os.getcwd()

        wdp_status = st_wdp_status.latex(state_uncertain)
        self._workdir_path = st_workdir_path.text_input(
            "Workdir:", value=workdir_path, help="absolute path to working directory"
        )
        wdp_status = wdp_status.latex(r"\checkmark")
        # wdp_button = st_wdp_button.button("Set")
        if os.path.isfile(os.path.join(self._workdir_path, "trainer_params.json")):
            wdp_status = wdp_status.latex(state_ok)
        if st_workdir_path:
            if os.path.isdir(self._workdir_path):
                config_io.set_config({"workdir": self._workdir_path, "config_path": start_config_path}, allow_new=True)
                if not os.path.isfile(os.path.join(self._workdir_path, "trainer_params.json")):
                    shutil.copy(
                        os.path.join(module_path, "templates", "trainer", "template_wd", "trainer_params.json"),
                        self._workdir_path,
                    )
            else:
                wdp_status = wdp_status.latex(state_failed)
                return -1
        return 0

    def save_train_params(self):
        with open(os.path.join(self._workdir_path, "trainer_params.json"), "w") as fp:
            json.dump(self.trainer_params_json, fp, indent=2)
