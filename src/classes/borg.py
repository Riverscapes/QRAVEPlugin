"""
Avoiding the Singleton Design Pattern with the Borg Idiom

Credit: Alex Martelli

https://www.oreilly.com/library/view/python-cookbook/0596001673/ch05s23.html
"""


class Borg:
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state


# class Example(Borg):
#     def __init__(self, name=None):
#         Borg.__init__(self)
#         if name is not None:
#             self.name = name
