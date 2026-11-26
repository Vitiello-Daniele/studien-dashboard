"""semester mit zugeordneten modulreferenzen"""


class Semester:
    def __init__(self, nummer: int) -> None:
        if type(nummer) is not int or nummer <= 0:
            raise ValueError("die semesternummer muss eine positive ganzzahl sein")

        self._nummer = nummer
        self._module = []
        self._studiengang = None

    @property
    def nummer(self) -> int:
        return self._nummer

    @property
    def module(self) -> tuple:
        return tuple(self._module)
