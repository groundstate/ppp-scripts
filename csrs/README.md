# runcsrsppp.py
This script automates job submission to the CSRS-PPP service using their script and API.
In particular it does the necessary pre-processing of the RINEX observation files.

# Installation requirements
You will need:
 1. the script csrs_ppp_auto.py, obtainable from upon request by email to "Geodetic Reference Systems Information" (https://webapp.csrs-scrs.nrcan-rncan.gc.ca/geod/tools-outils/ppp.php)
 2. rinexlib.py and ottplib.py, available from the develop branch of https://github.com/openttp/openttp
 3. utilities/editrnxobs.py 
