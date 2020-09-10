from flask_2_ui5_py import make_list_items_json_serializable, get_message
from flask_restful import Resource

from plants_tagger.services.selection_services import build_taxon_tree


class SelectionResource(Resource):
    @staticmethod
    def get():
        taxon_tree = build_taxon_tree()
        make_list_items_json_serializable(taxon_tree)

        return {'Selection':  {'TaxonTree': taxon_tree},
                'message': get_message(f"Loaded selection data.")}, 200
