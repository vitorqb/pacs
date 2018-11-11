from pyrsistent import v, pvector
import attr


@attr.s()
class TablePopulator():
    """ A service that populates a Model with default data """

    # Callable[data -> object] used to create objects.
    _create_fun = attr.ib()

    # Callable[data -> boolean]. Returns whether an object already exists
    # or not.
    _exists_fun = attr.ib()

    # A list of data to create
    _model_data = attr.ib()

    # A function used to print
    _printfun = attr.ib(default=print)

    # Stores created objects.
    _created_objects = attr.ib(factory=v, init=False)

    def __call__(self):
        """ Populates the db, creating all uncreated objects """
        self._printfun(f"Creating objects... ", end="")
        to_create = pvector(x for x in self._model_data if not self._exists_fun(x))
        for data in to_create:
            self._created_objects += [self._create_fun(data)]
        self._printfun(
            f"Created objects: {[x.name for x in self._created_objects]}"
        )
