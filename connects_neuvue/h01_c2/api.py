import datajoint as dj
from ..utils import (
    file_utils as fileu,
    nx_graph_utils as nxgu,
    dj_utils as dju
)

class API:
    def __init__(
        self,
        dj_host = None,
        dj_user = None,
        dj_password = None,
        **kwargs):
        try:
            if dj_host is not None:
                dj.conn(host=dj_host, user=dj_user, password=dj_password)
            else:
                dj.conn()
        except dj.errors.OperationalError:
            raise ValueError(
                "DataJoint connection failed. Check your credentials and network connection."
            )
        from .schema import AutoProofreadNeuron
        
        self.autoproof_table = AutoProofreadNeuron
        self.autoproof_obj_table = self.autoproof_table.Obj

    def nx_graph_autoproof_from_segment_id(
        self,
        segment_id,
        split_index = 0,
        add_bounding_box = True):
        restr_table = (self.autoproof_obj_table & dict(
            segment_id=segment_id,
            split_index = split_index
            )
        )
        G_file = restr_table.fetch1('neuron_graph')
        G = fileu.decompress_pickle(G_file)
        if add_bounding_box:
            nxgu.add_bounding_boxes_to_graph(G)
        return G
    
    def autoproof_segment_metadata_df(self,table=None):
        if table is None:
            table = self.autoproof_table
        return dju.df_from_table(table)
    