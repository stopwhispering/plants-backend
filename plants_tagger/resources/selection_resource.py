from flask_2_ui5_py import make_list_items_json_serializable, get_message, throw_exception
from flask_restful import Resource
from pydantic.error_wrappers import ValidationError

from plants_tagger.validation.selection_validation import PResultsSelection
from plants_tagger.services.selection_services import build_taxon_tree


class SelectionResource(Resource):
    """build & return taxon tree for advanced filtering"""

    @staticmethod
    def get():
        taxon_tree = build_taxon_tree()
        make_list_items_json_serializable(taxon_tree)

        results = {'action':    'Get taxon tree',
                   'resource':  'SelectionResource',
                   'message':   get_message(f"Loaded selection data."),
                   'Selection': {'TaxonTree': taxon_tree}}

        # evaluate output
        try:
            PResultsSelection(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200
