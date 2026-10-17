# IEEE four-node transformer reference facts

The five CSVs are unchanged numeric tables from the Power Grid Model IO
project, commit `4cb5f85c7e361bd68243036ca255d2100ed0a937`, directory
`_network_data_generation/ieee_4_node`:
https://github.com/PowerGridModel/power-grid-model-io/tree/4cb5f85c7e361bd68243036ca255d2100ed0a937/_network_data_generation/ieee_4_node

SPDX-FileCopyrightText: Contributors to the Power Grid Model project

SPDX-License-Identifier: MPL-2.0

License: https://www.mozilla.org/en-US/MPL/2.0/

The upstream authors identify the result tables as transcriptions of IEEE
published results, not newly computed oracle outputs. Their generation script
and data documentation explain the transformer, wire and loading conventions:
https://power-grid-model-io.readthedocs.io/en/stable/networks/ieee_4_node.html

The original IEEE test feeder describes the transformer benchmark, not an
operating customer installation:
https://ewh.ieee.org/soc/pes/dsacom/testfeeders/testfeeders.pdf

R/X entries are ohm/mile. Primary/secondary lengths are 2000/2500 feet.
Voltages are LN on wye sides, LL on delta sides; angles are degrees. Currents
are conductor currents, not delta winding currents. The test source is 12.47 kV
LL, 60 Hz, fixed voltage; transformer is 6000 kVA, R=1%, X=6% (|Z|=sqrt(37)%).
Secondary is 4.16 or 24.9 kV. Balanced loads are 1800 kW/phase at pf=.9;
unbalanced loads are 1275/1800/2375 kW at pf=.85/.9/.95. Shunt excitation and
line capacitance are excluded in this reference model.

Q11 uses the ynyn and dyn rows only: 8 cases. Other rows are retained unchanged
for source integrity but are NOT claimed as qualified. Neutral is reduced
into the line matrices. No explicit neutral voltage or insulation study is
validated. The server never imports these datasets or another reference solver.
