#include <stdio.h>
#include "hocdec.h"
#define IMPORT extern __declspec(dllimport)
IMPORT int nrnmpi_myid, nrn_nobanner_;

extern void _BK_reg();
extern void _CaV12_reg();
extern void _CaV22_reg();
extern void _HCN_reg();
extern void _KA14_reg();
extern void _KA34_reg();
extern void _KM_reg();
extern void _KV21_reg();
extern void _NaCX_reg();
extern void _NaV7_reg();
extern void _NaV9_reg();
extern void _NakpumpSchild_reg();
extern void _SK_reg();
extern void _caextscale_reg();
extern void _caintscale_reg();
extern void _extrapump_reg();
extern void _k_ion_dynamics_reg();
extern void _leak_reg();
extern void _na_ion_dynamics_reg();
extern void _newNaV8_reg();

void modl_reg(){
	//nrn_mswindll_stdio(stdin, stdout, stderr);
    if (!nrn_nobanner_) if (nrnmpi_myid < 1) {
	fprintf(stderr, "Additional mechanisms from files\n");

fprintf(stderr," BK.mod");
fprintf(stderr," CaV12.mod");
fprintf(stderr," CaV22.mod");
fprintf(stderr," HCN.mod");
fprintf(stderr," KA14.mod");
fprintf(stderr," KA34.mod");
fprintf(stderr," KM.mod");
fprintf(stderr," KV21.mod");
fprintf(stderr," NaCX.mod");
fprintf(stderr," NaV7.mod");
fprintf(stderr," NaV9.mod");
fprintf(stderr," NakpumpSchild.mod");
fprintf(stderr," SK.mod");
fprintf(stderr," caextscale.mod");
fprintf(stderr," caintscale.mod");
fprintf(stderr," extrapump.mod");
fprintf(stderr," k_ion_dynamics.mod");
fprintf(stderr," leak.mod");
fprintf(stderr," na_ion_dynamics.mod");
fprintf(stderr," newNaV8.mod");
fprintf(stderr, "\n");
    }
_BK_reg();
_CaV12_reg();
_CaV22_reg();
_HCN_reg();
_KA14_reg();
_KA34_reg();
_KM_reg();
_KV21_reg();
_NaCX_reg();
_NaV7_reg();
_NaV9_reg();
_NakpumpSchild_reg();
_SK_reg();
_caextscale_reg();
_caintscale_reg();
_extrapump_reg();
_k_ion_dynamics_reg();
_leak_reg();
_na_ion_dynamics_reg();
_newNaV8_reg();
}
