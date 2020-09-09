# cython: language_level=3
# cython: boundscheck=False, wraparound=False
# @formatter:off
from antidote.core.container cimport DependencyContainer
# @formatter:on

cpdef DependencyContainer get_container()
