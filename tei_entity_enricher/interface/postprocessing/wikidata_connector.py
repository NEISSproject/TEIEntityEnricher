from typing import Union, List, Tuple, Dict
from SPARQLWrapper import SPARQLWrapper, JSON
from tei_entity_enricher.interface.postprocessing.io import FileReader, FileWriter
from tei_entity_enricher.util.exceptions import FileNotFound
from tei_entity_enricher.util.helper import local_save_path, makedir_if_necessary
from tei_entity_enricher import __version__
import math
import os


class WikidataConnector:
    def __init__(
        self,
        input: Union[List[Tuple[str, str]], None] = None,
        check_connectivity: bool = True,
        wikidata_web_api_language: str = "de",
        wikidata_web_api_limit: str = "50",
        show_printmessages: bool = True,
    ) -> None:
        """establishes connection to wikidata web api and wikidata´s sparql endpoint,
        used to get a list of possible entities refering to input name and type strings

        input:
            contains a list of tuples, which themself consists of a name and a type string
        check_connectivity:
            execute connectivity check in __init__() or not (see connectivity_check())
        wikidata_web_api_language:
            language setting of wikidata web api (language in which the results are shown ('uselang' parameter) and language defining the domain in which data is searched for ('language' parameter of wbsearchentities action))
        wikidata_web_api_limit:
            maximum amount of returned search hits in wikidata web api query results
        show_printmessages:
            show class internal printmessages on runtime or not
        self.wikidata_web_api_baseUrl:
            baseUrl of wikidata web api, contains search string, language and limit of resulting hits placeholder
        connection_established:
            data from an api has already been received or not"""
        print("initializing WikidataConnector..") if show_printmessages else None
        self.input: Union[List[Tuple[str, str]], None] = input
        self.check_connectivity: bool = check_connectivity
        self.show_printmessages: bool = show_printmessages
        self.wikidata_web_api_baseUrl: str = "https://www.wikidata.org/w/api.php?action=wbsearchentities&search={}&format=json&language={}&uselang={}&limit={}"
        self.wikidata_web_api_language: str = wikidata_web_api_language
        self.wikidata_web_api_limit: str = wikidata_web_api_limit
        self.link_suggestion_categories_filepath: str = os.path.join(
            local_save_path, "config", "postprocessing", "link_sugesstion_categories.json"
        )
        try:
            self.link_suggestion_categories: Union[dict, None] = FileReader(
                filepath=self.link_suggestion_categories_filepath,
                origin="local",
                internal_call=True,
                show_printmessages=False,
            ).loadfile_json()
        except FileNotFound:
            print(
                "WikidataConnector: could not find link_sugesstion_categories.json in config dir. creating file with default settings..."
            ) if self.show_printmessages else None
            self.link_suggestion_categories: dict = {
                "person": [
                    ["Q5"],
                    "q5 = human",
                    True,
                ],
                "organisation": [
                    ["Q43229"],
                    "Q43229 = organization",
                    True,
                ],
                "place": [
                    ["Q515", "Q27096213"],
                    "Q515 = city, Q27096213 = geographic entity",
                    True,
                ],
            }
            try:
                makedir_if_necessary(os.path.dirname(self.link_suggestion_categories_filepath))
                FileWriter(
                    data=self.link_suggestion_categories,
                    filepath=self.link_suggestion_categories_filepath,
                    show_printmessages=False,
                ).writefile_json()
            except:
                print(
                    f"WikidataConnector __init__(): could not create default link_sugesstion_categories.json in config folder."
                ) if self.show_printmessages == True else None
        self.connection_established: bool = False
        if self.check_connectivity == True:
            self.connectivity_check()
        else:
            print(
                "WikidataConnector: initialization has been done without connectivity check."
            ) if self.show_printmessages else None

    def connectivity_check(self) -> int:
        """checking wikidata web api (preset query string: 'Berlin', hit limit: '1')
        and wikidata sparql endpoint (preset query input: ('Q64 (Berlin)', 'place')),
        returns 0 or -1 for unittest purposes"""

        def check_wikidata_web_api() -> bool:
            try:
                result = FileReader(
                    filepath=self.wikidata_web_api_baseUrl.format(
                        "Berlin",
                        self.wikidata_web_api_language,
                        self.wikidata_web_api_language,
                        "1",
                    ),
                    origin="web",
                    internal_call=True,
                    show_printmessages=self.show_printmessages,
                ).loadfile_json()
            except:
                print(
                    "WikidataConnector connectivity_check() error: no connection to wikidata web api"
                ) if self.show_printmessages else None
                return False
            if type(result) == dict:
                return True
            return False

        def check_wikidata_sparql_endpoint() -> bool:
            try:
                result = self.check_wikidata_entity_type("Q64", "place")
            except:
                print(
                    "WikidataConnector connectivity_check() error: internal failure in check_wikidata_sparql_endpoint() trying to do sparql query on wikidata sparql endpoint"
                ) if self.show_printmessages else None
                return False
            if type(result) == bool:
                return True
            print(
                "WikidataConnector connectivity_check() error: no connection to wikidata sparql endpoint"
            ) if self.show_printmessages else None
            return False

        if self.check_connectivity == False:
            self.check_connectivity == True
        if all((check_wikidata_web_api(), check_wikidata_sparql_endpoint())):
            print(
                "WikidataConnector connectivity_check() passed: Wikidata web api and wikidata sparql endpoint are responding as expected."
            ) if self.show_printmessages else None
            self.connection_established = True
            return 0
        return -1

    def get_wikidata_search_results(
        self,
        filter_for_precise_spelling: bool = True,
        filter_for_correct_type: bool = True,
    ) -> Union[Dict[Tuple[str, str], list], bool]:
        """sends a entity query to wikidata web api using input strings of self.input
        and returns a dict with input strings as keys and a list as values,
        which consists of the number of search hits and the returned data object

        filter_for_precise_spelling:
            variable determines wheather only exact matches
            between the search string and the label value in the search list returned by
            api are returned (filtering is executed only if there are more than 5 search hits,
            otherwise it is not executed although filter_for_precise_spelling is True),
        filter_for_correct_type:
            variable determines wheather the entities returned by api
            will be checked semantically with sparql queries in correspondance with the delivered
            type strings in self.input; only entities of a correct type will be returned"""
        if self.input == None:
            print(
                "WikidataConnector get_wikidata_search_results() internal error: WikidataConnector has no input data."
            ) if self.show_printmessages == True else None
            return False
        if (
            (type(self.input) != list)
            or (len(self.input) < 1)
            or (type(self.input[0]) != tuple)
            or (type(self.input[0][0]) != str)
        ):
            print(
                "WikidataConnector get_wikidata_search_results() internal error: WikidataConnector input data is in a wrong format."
            ) if self.show_printmessages == True else None
            return False
        result_dict = {}
        for string_tuple in self.input:
            filereader = FileReader(
                filepath=self.wikidata_web_api_baseUrl.format(
                    string_tuple[0],
                    self.wikidata_web_api_language,
                    self.wikidata_web_api_language,
                    self.wikidata_web_api_limit,
                ),
                origin="web",
                internal_call=True,
                show_printmessages=self.show_printmessages,
            )
            try:
                filereader_result = filereader.loadfile_json()
            except:
                print("WikidataConnector get_wikidata_search_results() error: internal failure")
                return False
            if all(x == False for x in [filter_for_precise_spelling, filter_for_correct_type]):
                print(f"no filtering in {string_tuple} result") if self.show_printmessages == True else None
            if filter_for_precise_spelling == True:
                precise_spelling = []
                entry_amount = len(filereader_result["search"])
                if entry_amount > 5:
                    percent = 100 / entry_amount if entry_amount > 0 else 100
                    progressbar = 0
                    for search_list_element in filereader_result["search"]:
                        progressbar += percent
                        print(
                            f"spell filtering in {string_tuple}-query results: {math.floor(progressbar * 10 ** 2) / 10 ** 2}"
                        ) if self.show_printmessages == True else None
                        if search_list_element["match"]["text"].lower() == string_tuple[0].lower():
                            precise_spelling.append(search_list_element)
                    filereader_result["search"] = precise_spelling
            if filter_for_correct_type == True:
                correctly_typed_entities = []
                entry_amount = len(filereader_result["search"])
                percent = 100 / entry_amount if entry_amount > 0 else 100
                progressbar = 0
                for search_list_element in filereader_result["search"]:
                    progressbar += percent
                    print(
                        f"type filtering in {string_tuple} result: {math.floor(progressbar * 10 ** 2) / 10 ** 2}"
                    ) if self.show_printmessages == True else None
                    if self.check_wikidata_entity_type(search_list_element["id"], string_tuple[1]) == True:
                        correctly_typed_entities.append(search_list_element)
                filereader_result["search"] = correctly_typed_entities
            result_dict[string_tuple] = [
                len(filereader_result["search"]),
                filereader_result,
            ]
        return result_dict

    def check_wikidata_entity_type(self, entity_id: str, type: str) -> Union[bool, None]:
        """used in get_wikidata_search_results() to check, if those wikidata entities delivered
        by self.get_wikidata_search_results() query are of the type, which has been defined inside
        the self.input tuples of WikidataConnector class

        this check uses the wikidata semantic web data base by sending queries to the wikidata sparql endpoint;
        get_wikidata_search_results() retrieves wikidata id numbers, which are used here in an ASK-query,
        which determines, if the entity in question is a member of one of specific classes
        (see local 'query_string' variable for details: 'wdt:P31/wdt:P279*'-property means 'is a member of a specific class or
        a member of any subclass (any level beneath) of a specific class' and the FILTER statement
        (created with local function _build_filter_string() on basis of data from self.link_suggestion_categories)
        defines a set of classes, out of which only one class has to match the query statement to let the query return true)

        a sparqle query to wikidata endpoint needs an agent parameter in the header to get an answer,
        the value of the agent string can be choosen freely

        this method checks only one entity at once and has to be used in an iteration

        it contains an internal auxiliary function _build_filter_string
        to create the filter expression for the sparql query"""

        def _build_filter_string(type_string) -> str:
            filter_string = "("
            type_checking_entity_list = self.link_suggestion_categories.get(type)[0]
            for index, x in enumerate(type_checking_entity_list):
                if index != len(type_checking_entity_list) - 1:
                    filter_string += "wd:" + x + ", "
                else:
                    filter_string += "wd:" + x + ")"
            return filter_string

        if type not in list(self.link_suggestion_categories.keys()):
            return None
        endpoint_url = "https://query.wikidata.org/sparql"
        user_agent = "NEISS TEI Entity Enricher v.{}".format(__version__)
        sparql = SPARQLWrapper(endpoint=endpoint_url, agent=user_agent)
        query_string = """
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>
            PREFIX wd: <http://www.wikidata.org/entity/>

            ASK
            {
            wd:%s wdt:P31/wdt:P279* ?o .
            FILTER (?o IN %s)
            }
        """ % (
            entity_id,
            _build_filter_string(type),
        )
        sparql.setQuery(query_string)
        sparql.setReturnFormat(JSON)
        result = sparql.query().convert()
        return result["boolean"]
