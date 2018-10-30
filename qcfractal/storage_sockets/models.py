import mongoengine as db
import datetime


class Collection(db.DynamicDocument):
    """
        A collection of precomuted workflows such as datasets, ..

        This is a dynamic document, so it will accept any number of
        extra fields (expandable and uncontrolled schema)
    """

    collection_type = db.StringField(default='', required=True,
                                     choices=['dataset', '?'])
    name = db.StringField(default='', required=True)  # Example 'water'

    meta = {
        'collection': 'collections',  # DB collection/table name
        'indexes': [
            {'fields': ('collection_type', 'name'), 'unique': True}
        ]
    }

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Molecule(db.DynamicDocument):
    """
        The molecule DB collection is managed by pymongo, so far
    """

    name = db.StringField()
    molecular_formula = db.StringField()
    molecule_hash = db.StringField()

    def create_hash(self):
        """ TODO: create a special hash before saving"""
        return ''

    def save(self, *args, **kwargs):
        """Override save to add molecule_hash"""
        # self.molecule_hash = self.create_hash()

        return super(Molecule, self).save(*args, **kwargs)

    meta = {
        'collection': 'molecules',
        'indexes': [
            {'fields': ('molecule_hash', 'molecular_formula'), 'unique': True}
        ]
    }

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Options(db.DynamicDocument):
    """
        Options are unique for a specific program and name
    """

    program = db.StringField(required=True)
    # TODO: choose a more descriptive name, like options_type
    option_name = db.StringField(default='default', required=True)

    # program specific
    # e_convergence = db.IntField()
    # d_convergence = db.IntField()
    # dft_spherical_points = db.IntField()
    # dft_radial_points = db.IntField()
    # maxiter = db.IntField()
    # scf_type = db.StringField()
    # mp2_type = db.StringField()
    # freeze_core = db.BooleanField()

    meta = {
        'indexes': [
            {'fields': ('program', 'option_name'), 'unique': True}
        ]
    }

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class BaseResult(db.DynamicDocument):
    """
        Abstract Base class for Results and Procedures
    """

    # queue related
    task_queue_id = db.StringField()  # ObjectId, reference task_queue but without validation
    status = db.StringField(default='INCOMPLETE', choices=['COMPLETE', 'INCOMPLETE', 'ERROR'])

    meta = {
        'abstract': True,
        # 'allow_inheritance': True,
        'indexes': [
            'status'
        ]
    }


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Result(BaseResult):
    """
        Hold the result of an atomic single calculation
    """

    # uniquely identifying a result
    program = db.StringField(required=True)  # example "rdkit", is it the same as program in options?
    driver = db.StringField(required=True)  # example "gradient"
    method = db.StringField(required=True)  # example "uff"
    basis = db.StringField()
    molecule = db.ReferenceField(Molecule, required=True)   # or LazyReferenceField if only ID is needed?
    options = db.LazyReferenceField(Options)  # ** has to be a FK or empty, can't be a string

    # output related
    properties = db.DynamicField()  # accept any, no validation
    return_result = db.DynamicField()  # better performance than db.ListField(db.FloatField())
    provenance = db.DynamicField()  # or an Embedded Documents with a structure?
        #  {"creator": "rdkit", "version": "2018.03.4",
        # "routine": "rdkit.Chem.AllChem.UFFGetMoleculeForceField",
        # "cpu": "Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz", "hostname": "x1-carbon6", "username": "doaa",
        # "wall_time": 0.14191770553588867},

    schema_name = db.StringField(default="qc_ret_data_output")
    schema_version = db.IntField()  # or String?

    meta = {
        'collection': 'result',
        'indexes': [
           {'fields': ('program', 'driver', 'method', 'basis',
                       'molecule', 'options'), 'unique': True},
        ]
    }

    # def save(self, *args, **kwargs):
    #     """Override save to handle options"""
    #
    #     print('Options before: ', self.options)
    #     if not isinstance(self.options, Options):
    #         self.options = Options(program=self.program, option_name='default').update(upsert=True, full_result=True)
    #         print('Options after: ', self.options)
    #
    #     return super(Result, self).save(*args, **kwargs)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Procedure(BaseResult):
    """
        A procedure is a group of related results applied to a list of molecules

        TODO: this looks exactly like results except those attributes listed here
    """

    procedure_type = db.StringField(required=True)  # example: 'optimization', 'single'
    # Todo: change name to be different from results program
    procedure_program = db.StringField(required=True)  # example: 'Geometric'
    procedure_options = db.ReferenceField(Options)  # options of the procedure

    qc_meta = db.DynamicField()  # --> all inside results

    meta = {
        'collection': 'procedure',
        'allow_inheritance': True,
        'indexes': [
            # TODO: needs a unique index, + molecule?
            {'fields': ('procedure_type', 'procedure_program'), 'unique': False}  # TODO: check
        ]
    }

# ================== Types of Procedures ================== #


class OptimizationProcedure(Procedure):
    """
        An Optimization  procedure
    """

    procedure_type = db.StringField(default='optimization', required=True)

    initial_molecule = db.ReferenceField(Molecule)  # always load with select_related
    final_molecule = db.ReferenceField(Molecule)

    # output
    trajectory = db.ListField(Result)

    meta = {
        'indexes': [
            {'fields': ('initial_molecule', 'procedure_type', 'procedure_program'), 'unique': False}  # TODO: check
        ]
    }


class TorsiondriveProcedure(Procedure):
    """
        An torsion drive  procedure
    """

    procedure_type = db.StringField(default='torsiondrive', required=True)

    # TODO: add more fields

    meta = {
        'indexes': [
        ]
    }

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Spec(db.DynamicEmbeddedDocument):
    """ The spec of a task in the queue
        This is an embedded document, meaning that it will be embedded
        in the task_queue collection and won't be stored as a seperate
        collection/table --> for faster parsing
    """

    function = db.StringField()
    args = db.DynamicField()    # fast, can take any structure
    kwargs = db.DynamicField()


class TaskQueue(db.DynamicDocument):
    """A queue of tasks corresponding to a procedure"""

    spec = db.EmbeddedDocumentField(Spec, default=Spec)

    # others
    hooks = db.ListField(db.DynamicField())  # ??
    tag = db.ListField()  # or str
    parser = db.StringField(default='')
    status = db.StringField(default='WAITING',
                            choices=['RUNNING', 'WAITING', 'ERROR', 'COMPLETE'])

    created_on = db.DateTimeField(required=True, default=datetime.datetime.now)
    modified_on = db.DateTimeField(required=True, default=datetime.datetime.now)

    baseResult = db.ReferenceField(BaseResult)  # can reference Results or any Procedure

    meta = {
        'indexes': [
            'created_on',
            'status'

        ]
        # 'indexes': [
        #         '$function', # text index, not needed
        #         '#function', # hash index
        #         ('title', '-rating'),  # rating is descending, direction only for multi-indices
        #     {
        #       'fields': ('spec.function', 'tag'),
        #       'unique': True
        #     }
        # ]
    }

    def save(self, *args, **kwargs):
        """Override save to update modified_on"""
        self.modified_on = datetime.datetime.now()

        return super(TaskQueue, self).save(*args, **kwargs)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class ServiceQueue(db.DynamicDocument):
    pass

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
