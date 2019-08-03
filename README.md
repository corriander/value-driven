Tools for Value-Driven Design
=============================

![Build Status][master-build-status]


Tools intended to help with modelling decisions in a value centric
design process. The intent is to keep this as generic as possible, as
some of this decision modelling is suited to generic decision-making,
non-design activities with a little massaging.

Features
-------

  - Concept Design Analysis (CODA) method implementation
  - Requirements weighting with a Binary Weighting Matrix
  - Programmatic or Excel-based models

Install
-------

	pip install vdd

Roadmap
-------

![Azure DevOps builds (branch)][develop-build-status]

  - Model sets for comparative work (rather than a single set of
	characteristic parameter values)
  - Improved visualisation
  - Export CODA models to Excel template
  - House of Quality style requirement/characteristic weighting

References
----------

Based on my own degree notes and open access literature:

  - M.H. Eres et al, 2014. Mapping Customer Needs to Engineering
	Characteristics: An Aerospace Perspective for Conceptual Design -
	Journal of Engineering Design pp. 1-24
	<http://eprints.soton.ac.uk/id/eprint/361442>

<!-- statuses -->
[master-build-status]: https://dev.azure.com/corriander/code-projects/_apis/build/status/corriander.vdd?branchName=master
[develop-build-status]: https://img.shields.io/azure-devops/build/corriander/d4da21a7-9ca1-4ecd-a01c-790771205d03/1/develop?label=develop&style=plastic
