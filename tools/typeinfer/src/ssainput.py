
ssa_text = """
       0 [0xffffffffffffffff]: FunctionStart(ILA(1))
       1 [0x4011cd]: v1 = v0
       2 [0x4011cd]: v3 = IntSub(v2, $0x8)
       3 [0x4011cd]: Store8(v3, v1)
       4 [0x4011ce]: v4 = v3
       5 [0x4011d1]: v5 = IntLess(v3, $0x30)
       6 [0x4011d1]: v6 = IntSBorrow(v3, $0x30)
       7 [0x4011d1]: v7 = IntSub(v3, $0x30)
       8 [0x4011d1]: v8 = IntSLess(v7, $0x0)
       9 [0x4011d1]: v9 = IntEqual(v7, $0x0)
      10 [0x4011d1]: v10 = IntAnd(v7, $0xff)
      11 [0x4011d1]: v11 = Popcount(v10)
      12 [0x4011d1]: v12 = IntAnd(v11, $0x1)
      13 [0x4011d1]: v13 = IntEqual(v12, $0x0)
      14 [0x4011d5]: v14 = IntAdd(v4, $0xffffffffffffffd8)
      15 [0x4011d5]: v16 = v15
      16 [0x4011d5]: Store8(v14, v16)
      17 [0x4011d9]: v17 = IntAdd(v4, $0xffffffffffffffd4)
      18 [0x4011d9]: v19 = v18
      19 [0x4011d9]: Store4(v17, v19)
      20 [0x4011dc]: v20 = IntAdd(v4, $0xffffffffffffffd4)
      21 [0x4011dc]: v21 = Load4(v20)
      22 [0x4011dc]: v22 = v21
      23 [0x4011dc]: v23 = IntLess(v22, $0x0)
      24 [0x4011dc]: v24 = IntSBorrow(v22, $0x0)
      25 [0x4011dc]: v25 = IntSub(v22, $0x0)
      26 [0x4011dc]: v26 = IntSLess(v25, $0x0)
      27 [0x4011dc]: v27 = IntEqual(v25, $0x0)
      28 [0x4011dc]: v28 = IntAnd(v25, $0xff)
      29 [0x4011dc]: v29 = Popcount(v28)
      30 [0x4011dc]: v30 = IntAnd(v29, $0x1)
      31 [0x4011dc]: v31 = IntEqual(v30, $0x0)
      32 [0x4011e0]: v32 = BoolNegate(v27)
      33 [0x4011e0]: Cbranch(ILA(36), v32)
      34 [0x4011e2]: v33 = $0x0
      35 [0x4011e7]: Branch(ILA(138))
      36 [0x4011e9]: v34 = IntAdd(v4, $0xffffffffffffffd8)
      37 [0x4011e9]: v35 = Load8(v34)
      38 [0x4011e9]: v36 = v35
      39 [0x4011ed]: v37 = Load8(v36)
      40 [0x4011ed]: v38 = v37
      41 [0x4011f0]: v39 = v38
      42 [0x4011f3]: v40 = IntSub(v7, $0x8)
      43 [0x4011f3]: Store8(v40, $0x4011f8)
      44 [0x4011f3]: CallWithFallthrough(MCA(0x401176))
      45 [0x4011f3]: v41 = IntAdd(v40, $0x8)
      46 [0x4011f8]: v42 = IntAdd(v4, $0xffffffffffffffe8)
      47 [0x4011f8]: v44 = v43
      48 [0x4011f8]: Store8(v42, v44)
      49 [0x4011fc]: v45 = IntAdd(v4, $0xffffffffffffffe8)
      50 [0x4011fc]: v46 = Load8(v45)
      51 [0x4011fc]: v47 = v46
      52 [0x401200]: v48 = IntAdd(v4, $0xfffffffffffffff8)
      53 [0x401200]: v49 = v47
      54 [0x401200]: Store8(v48, v49)
      55 [0x401204]: v50 = IntAdd(v4, $0xfffffffffffffff4)
      56 [0x401204]: v51 = $0x1
      57 [0x401204]: Store4(v50, v51)
      58 [0x40120b]: Branch(ILA(117))
      59 [0x40120d]: v52 = IntAdd(v4, $0xfffffffffffffff4)
      60 [0x40120d]: v53 = Load4(v52)
      61 [0x40120d]: v54 = v53
      62 [0x40120d]: v55 = IntZext(v54)
      63 [0x401210]: v56 = IntSext(v55)
      64 [0x401212]: v57 = IntMult(v56, $0x8)
      65 [0x401212]: v58 = v57
      66 [0x40121a]: v59 = IntAdd(v4, $0xffffffffffffffd8)
      67 [0x40121a]: v60 = Load8(v59)
      68 [0x40121a]: v61 = v60
      69 [0x40121e]: v62 = IntCarry(v61, v58)
      70 [0x40121e]: v63 = IntSCarry(v61, v58)
      71 [0x40121e]: v64 = IntAdd(v61, v58)
      72 [0x40121e]: v65 = IntSLess(v64, $0x0)
      73 [0x40121e]: v66 = IntEqual(v64, $0x0)
      74 [0x40121e]: v67 = IntAnd(v64, $0xff)
      75 [0x40121e]: v68 = Popcount(v67)
      76 [0x40121e]: v69 = IntAnd(v68, $0x1)
      77 [0x40121e]: v70 = IntEqual(v69, $0x0)
      78 [0x401221]: v71 = Load8(v64)
      79 [0x401221]: v72 = v71
      80 [0x401224]: v73 = v72
      ... v75 = 𝛟(v41, v74)
      81 [0x401227]: v76 = IntSub(v75, $0x8)
      82 [0x401227]: Store8(v76, $0x40122c)
      83 [0x401227]: CallWithFallthrough(MCA(0x401176))
      84 [0x401227]: v74 = IntAdd(v76, $0x8)
      85 [0x40122c]: v77 = IntAdd(v4, $0xfffffffffffffff8)
      86 [0x40122c]: v78 = Load8(v77)
      87 [0x40122c]: v79 = v78
      88 [0x401230]: v80 = IntAdd(v79, $0x8)
      89 [0x401230]: v82 = v81
      90 [0x401230]: Store8(v80, v82)
      91 [0x401234]: v83 = IntAdd(v4, $0xfffffffffffffff8)
      92 [0x401234]: v84 = Load8(v83)
      93 [0x401234]: v85 = v84
      94 [0x401238]: v86 = IntAdd(v85, $0x8)
      95 [0x401238]: v87 = Load8(v86)
      96 [0x401238]: v88 = v87
      97 [0x40123c]: v89 = IntAdd(v4, $0xfffffffffffffff8)
      98 [0x40123c]: v90 = v88
      99 [0x40123c]: Store8(v89, v90)
     100 [0x401240]: v91 = IntAdd(v4, $0xfffffffffffffff4)
     101 [0x401240]: v92 = Load4(v91)
     102 [0x401240]: v93 = IntCarry(v92, $0x1)
     103 [0x401240]: v94 = Load4(v91)
     104 [0x401240]: v95 = IntSCarry(v94, $0x1)
     105 [0x401240]: v96 = Load4(v91)
     106 [0x401240]: v97 = IntAdd(v96, $0x1)
     107 [0x401240]: Store4(v91, v97)
     108 [0x401240]: v98 = Load4(v91)
     109 [0x401240]: v99 = IntSLess(v98, $0x0)
     110 [0x401240]: v100 = Load4(v91)
     111 [0x401240]: v101 = IntEqual(v100, $0x0)
     112 [0x401240]: v102 = Load4(v91)
     113 [0x401240]: v103 = IntAnd(v102, $0xff)
     114 [0x401240]: v104 = Popcount(v103)
     115 [0x401240]: v105 = IntAnd(v104, $0x1)
     116 [0x401240]: v106 = IntEqual(v105, $0x0)
     117 [0x401244]: v107 = IntAdd(v4, $0xfffffffffffffff4)
     118 [0x401244]: v108 = Load4(v107)
     119 [0x401244]: v109 = v108
     120 [0x401244]: v110 = IntZext(v109)
     121 [0x401247]: v111 = IntAdd(v4, $0xffffffffffffffd4)
     122 [0x401247]: v112 = Load4(v111)
     123 [0x401247]: v113 = v112
     124 [0x401247]: v114 = IntLess(v110, v113)
     125 [0x401247]: v115 = IntSBorrow(v110, v113)
     126 [0x401247]: v116 = IntSub(v110, v113)
     127 [0x401247]: v117 = IntSLess(v116, $0x0)
     128 [0x401247]: v118 = IntEqual(v116, $0x0)
     129 [0x401247]: v119 = IntAnd(v116, $0xff)
     130 [0x401247]: v120 = Popcount(v119)
     131 [0x401247]: v121 = IntAnd(v120, $0x1)
     132 [0x401247]: v122 = IntEqual(v121, $0x0)
     133 [0x40124a]: v123 = IntNotEqual(v115, v117)
     134 [0x40124a]: Cbranch(ILA(59), v123)
     135 [0x40124c]: v124 = IntAdd(v4, $0xffffffffffffffe8)
     136 [0x40124c]: v125 = Load8(v124)
     137 [0x40124c]: v126 = v125
     138 [0x401250]: v127 = v4
     139 [0x401250]: v128 = Load8(v127)
     140 [0x401250]: v129 = IntAdd(v127, $0x8)
     141 [0x401251]: v130 = Load8(v129)
     142 [0x401251]: v131 = IntAdd(v129, $0x8)
     143 [0x401251]: Return(v130)
     144 [0xffffffffffffffff]: FunctionEnd

"""





# ssa_text = """
#      308 [0x40111b]: v283 = IntAdd(v272, $0xfffffffffffffff8)
#      309 [0x40111b]: v284 = Load8(v283)
#      310 [0x40111b]: v285 = v284
#      311 [0x40111f]: v286 = IntAdd(v272, $0xffffffffffffffe8)
#      312 [0x40111f]: v287 = v285
#      313 [0x40111f]: Store8(v286, v287)
#      314 [0x401123]: v288 = IntAdd(v272, $0xffffffffffffffe8)
#      315 [0x401123]: v289 = Load8(v288)
#      316 [0x401123]: v290 = v289
#      317 [0x401127]: v291 = Load8(v290)
#      318 [0x401127]: v292 = v291
#      319 [0x40112a]: v293 = IntAdd(v272, $0xfffffffffffffff8)
#      320 [0x40112a]: v294 = v292
#      321 [0x40112a]: Store8(v293, v294)
# """




ssa_text = """
 0 [0xffffffffffffffff]: FunctionStart(ILA(1))
       1 [0x1028f7]: v1 = v0
       2 [0x1028f7]: v3 = IntSub(v2, $0x8)
       3 [0x1028f7]: Store8(v3, v1)
       4 [0x1028f8]: v4 = v3
       5 [0x1028fb]: v5 = IntAdd(v4, $0xffffffffffffffe8)
       6 [0x1028fb]: v7 = v6
       7 [0x1028fb]: Store8(v5, v7)
       8 [0x1028ff]: v8 = IntAdd(v4, $0xffffffffffffffe0)
       9 [0x1028ff]: v10 = v9
      10 [0x1028ff]: Store8(v8, v10)
      11 [0x102903]: v11 = IntAdd(v4, $0xffffffffffffffe8)
      12 [0x102903]: v12 = Load8(v11)
      13 [0x102903]: v13 = v12
      14 [0x102907]: v14 = IntAdd(v4, $0xfffffffffffffff0)
      15 [0x102907]: v15 = v13
      16 [0x102907]: Store8(v14, v15)
      17 [0x10290b]: v16 = IntAdd(v4, $0xffffffffffffffe0)
      18 [0x10290b]: v17 = Load8(v16)
      19 [0x10290b]: v18 = v17
      20 [0x10290f]: v19 = IntAdd(v18, $0xffffffffffffffff)
      21 [0x10290f]: v20 = v19
      22 [0x102913]: v21 = IntAdd(v4, $0xfffffffffffffff0)
      23 [0x102913]: v22 = Load8(v21)
      24 [0x102913]: v23 = v22
      25 [0x102917]: v24 = IntCarry(v23, v20)
      26 [0x102917]: v25 = IntSCarry(v23, v20)
      27 [0x102917]: v26 = IntAdd(v23, v20)
      28 [0x102917]: v27 = IntSLess(v26, $0x0)
      29 [0x102917]: v28 = IntEqual(v26, $0x0)
      30 [0x102917]: v29 = IntAnd(v26, $0xff)
      31 [0x102917]: v30 = Popcount(v29)
      32 [0x102917]: v31 = IntAnd(v30, $0x1)
      33 [0x102917]: v32 = IntEqual(v31, $0x0)
      34 [0x10291a]: v33 = IntAdd(v4, $0xfffffffffffffff8)
      35 [0x10291a]: v34 = v26
      36 [0x10291a]: Store8(v33, v34)
      37 [0x10291e]: v35 = IntAdd(v4, $0xfffffffffffffff8)
      38 [0x10291e]: v36 = Load8(v35)
      39 [0x10291e]: v37 = v36
      40 [0x102922]: v38 = $0x0
      41 [0x102927]: v39 = IntAdd(v4, $0xffffffffffffffe0)
      42 [0x102927]: v40 = Load8(v39)
      43 [0x102927]: v41 = IntZext(v40)
      44 [0x102927]: v42 = IntZext(v38)
      45 [0x102927]: v43 = IntLeftShift(v42, $0x40)
      46 [0x102927]: v44 = IntZext(v37)
      47 [0x102927]: v45 = IntOr(v43, v44)
      48 [0x102927]: v46 = IntUDiv(v45, v41)
      49 [0x102927]: v47 = SubPiece(v46, $0x0)
      50 [0x102927]: v48 = IntURem(v45, v41)
      51 [0x102927]: v49 = SubPiece(v48, $0x0)
      52 [0x10292b]: v50 = v49
      53 [0x10292e]: v51 = IntNotEqual(v50, $0x0)
      54 [0x10292e]: v52 = IntSBorrow($0x0, v50)
      55 [0x10292e]: v53 = IntTwosComp(v50)
      56 [0x10292e]: v54 = IntSLess(v53, $0x0)
      57 [0x10292e]: v55 = IntEqual(v53, $0x0)
      58 [0x10292e]: v56 = IntAnd(v53, $0xff)
      59 [0x10292e]: v57 = Popcount(v56)
      60 [0x10292e]: v58 = IntAnd(v57, $0x1)
      61 [0x10292e]: v59 = IntEqual(v58, $0x0)
      62 [0x102931]: v60 = v53
      63 [0x102934]: v61 = IntAdd(v4, $0xfffffffffffffff8)
      64 [0x102934]: v62 = Load8(v61)
      65 [0x102934]: v63 = v62
      66 [0x102938]: v64 = IntCarry(v63, v60)
      67 [0x102938]: v65 = IntSCarry(v63, v60)
      68 [0x102938]: v66 = IntAdd(v63, v60)
      69 [0x102938]: v67 = IntSLess(v66, $0x0)
      70 [0x102938]: v68 = IntEqual(v66, $0x0)
      71 [0x102938]: v69 = IntAnd(v66, $0xff)
      72 [0x102938]: v70 = Popcount(v69)
      73 [0x102938]: v71 = IntAnd(v70, $0x1)
      74 [0x102938]: v72 = IntEqual(v71, $0x0)
      75 [0x10293b]: v73 = $0x0
      76 [0x10293b]: v74 = Load8(v3)
      77 [0x10293b]: v75 = IntAdd(v3, $0x8)
      78 [0x10293b]: v76 = v74
      79 [0x10293c]: v77 = Load8(v75)
      80 [0x10293c]: v78 = IntAdd(v75, $0x8)
      81 [0x10293c]: Return(v77)
      82 [0xffffffffffffffff]: FunctionEnd
"""


ssa_text = """
       1 [0x4011cd]: v1 = v0
       2 [0x4011cd]: v3 = IntSub(v2, $0x8)
       3 [0x4011cd]: Store8(v3, v1)
       4 [0x4011ce]: v4 = v3
       5 [0x4011d1]: v5 = IntLess(v3, $0x30)
       6 [0x4011d1]: v6 = IntSBorrow(v3, $0x30)
       7 [0x4011d1]: v7 = IntSub(v3, $0x30)
       8 [0x4011d1]: v8 = IntSLess(v7, $0x0)
       9 [0x4011d1]: v9 = IntEqual(v7, $0x0)
      10 [0x4011d1]: v10 = IntAnd(v7, $0xff)
      11 [0x4011d1]: v11 = Popcount(v10)
      12 [0x4011d1]: v12 = IntAnd(v11, $0x1)
      13 [0x4011d1]: v13 = IntEqual(v12, $0x0)
      14 [0x4011d5]: v14 = IntAdd(v4, $0xffffffffffffffd8)
      15 [0x4011d5]: v16 = v15
      16 [0x4011d5]: Store8(v14, v16)
      17 [0x4011d9]: v17 = IntAdd(v4, $0xffffffffffffffd4)
      18 [0x4011d9]: v19 = v18
      19 [0x4011d9]: Store4(v17, v19)
      20 [0x4011dc]: v20 = IntAdd(v4, $0xffffffffffffffd4)
      21 [0x4011dc]: v21 = Load4(v20)
      22 [0x4011dc]: v22 = v21
      23 [0x4011dc]: v23 = IntLess(v22, $0x0)
      24 [0x4011dc]: v24 = IntSBorrow(v22, $0x0)
      25 [0x4011dc]: v25 = IntSub(v22, $0x0)
      26 [0x4011dc]: v26 = IntSLess(v25, $0x0)
      27 [0x4011dc]: v27 = IntEqual(v25, $0x0)
      28 [0x4011dc]: v28 = IntAnd(v25, $0xff)
      29 [0x4011dc]: v29 = Popcount(v28)
      30 [0x4011dc]: v30 = IntAnd(v29, $0x1)
      31 [0x4011dc]: v31 = IntEqual(v30, $0x0)
      32 [0x4011e0]: v32 = BoolNegate(v27)
      33 [0x4011e0]: Cbranch(ILA(36), v32)
      34 [0x4011e2]: v33 = $0x0
      35 [0x4011e7]: Branch(ILA(138))
      36 [0x4011e9]: v34 = IntAdd(v4, $0xffffffffffffffd8)
      37 [0x4011e9]: v35 = Load8(v34)
      38 [0x4011e9]: v36 = v35
      39 [0x4011ed]: v37 = Load8(v36)
      40 [0x4011ed]: v38 = v37
      41 [0x4011f0]: v39 = v38
      42 [0x4011f3]: v40 = IntSub(v7, $0x8)
      43 [0x4011f3]: Store8(v40, $0x4011f8)
      44 [0x4011f3]: CallWithFallthrough(MCA(0x401176))
      45 [0x4011f3]: v41 = IntAdd(v40, $0x8)
      46 [0x4011f8]: v42 = IntAdd(v4, $0xffffffffffffffe8)
      47 [0x4011f8]: v44 = v43
      48 [0x4011f8]: Store8(v42, v44)
      49 [0x4011fc]: v45 = IntAdd(v4, $0xffffffffffffffe8)
      50 [0x4011fc]: v46 = Load8(v45)
      51 [0x4011fc]: v47 = v46
      52 [0x401200]: v48 = IntAdd(v4, $0xfffffffffffffff8)
      53 [0x401200]: v49 = v47
      54 [0x401200]: Store8(v48, v49)
      55 [0x401204]: v50 = IntAdd(v4, $0xfffffffffffffff4)
      56 [0x401204]: v51 = $0x1
      57 [0x401204]: Store4(v50, v51)
      58 [0x40120b]: Branch(ILA(117))
      59 [0x40120d]: v52 = IntAdd(v4, $0xfffffffffffffff4)
      60 [0x40120d]: v53 = Load4(v52)
      61 [0x40120d]: v54 = v53
      62 [0x40120d]: v55 = IntZext(v54)
      63 [0x401210]: v56 = IntSext(v55)
      64 [0x401212]: v57 = IntMult(v56, $0x8)
      65 [0x401212]: v58 = v57
      66 [0x40121a]: v59 = IntAdd(v4, $0xffffffffffffffd8)
      67 [0x40121a]: v60 = Load8(v59)
      68 [0x40121a]: v61 = v60
      69 [0x40121e]: v62 = IntCarry(v61, v58)
      70 [0x40121e]: v63 = IntSCarry(v61, v58)
      71 [0x40121e]: v64 = IntAdd(v61, v58)
      72 [0x40121e]: v65 = IntSLess(v64, $0x0)
      73 [0x40121e]: v66 = IntEqual(v64, $0x0)
      74 [0x40121e]: v67 = IntAnd(v64, $0xff)
      75 [0x40121e]: v68 = Popcount(v67)
      76 [0x40121e]: v69 = IntAnd(v68, $0x1)
      77 [0x40121e]: v70 = IntEqual(v69, $0x0)
      78 [0x401221]: v71 = Load8(v64)
      79 [0x401221]: v72 = v71
      80 [0x401224]: v73 = v72
      ... v75 = 𝛟(v41, v74)
      81 [0x401227]: v76 = IntSub(v75, $0x8)
      82 [0x401227]: Store8(v76, $0x40122c)
      83 [0x401227]: CallWithFallthrough(MCA(0x401176))
      84 [0x401227]: v74 = IntAdd(v76, $0x8)
      85 [0x40122c]: v77 = IntAdd(v4, $0xfffffffffffffff8)
      86 [0x40122c]: v78 = Load8(v77)
      87 [0x40122c]: v79 = v78
      88 [0x401230]: v80 = IntAdd(v79, $0x8)
      89 [0x401230]: v82 = v81
      90 [0x401230]: Store8(v80, v82)
      91 [0x401234]: v83 = IntAdd(v4, $0xfffffffffffffff8)
      92 [0x401234]: v84 = Load8(v83)
      93 [0x401234]: v85 = v84
      94 [0x401238]: v86 = IntAdd(v85, $0x8)
      95 [0x401238]: v87 = Load8(v86)
      96 [0x401238]: v88 = v87
      97 [0x40123c]: v89 = IntAdd(v4, $0xfffffffffffffff8)
      98 [0x40123c]: v90 = v88
      99 [0x40123c]: Store8(v89, v90)
     100 [0x401240]: v91 = IntAdd(v4, $0xfffffffffffffff4)
     101 [0x401240]: v92 = Load4(v91)
     102 [0x401240]: v93 = IntCarry(v92, $0x1)
     103 [0x401240]: v94 = Load4(v91)
     104 [0x401240]: v95 = IntSCarry(v94, $0x1)
     105 [0x401240]: v96 = Load4(v91)
     106 [0x401240]: v97 = IntAdd(v96, $0x1)
     107 [0x401240]: Store4(v91, v97)
     108 [0x401240]: v98 = Load4(v91)
     109 [0x401240]: v99 = IntSLess(v98, $0x0)
     110 [0x401240]: v100 = Load4(v91)
     111 [0x401240]: v101 = IntEqual(v100, $0x0)
     112 [0x401240]: v102 = Load4(v91)
     113 [0x401240]: v103 = IntAnd(v102, $0xff)
     114 [0x401240]: v104 = Popcount(v103)
     115 [0x401240]: v105 = IntAnd(v104, $0x1)
     116 [0x401240]: v106 = IntEqual(v105, $0x0)
     117 [0x401244]: v107 = IntAdd(v4, $0xfffffffffffffff4)
     118 [0x401244]: v108 = Load4(v107)
     119 [0x401244]: v109 = v108
     120 [0x401244]: v110 = IntZext(v109)
     121 [0x401247]: v111 = IntAdd(v4, $0xffffffffffffffd4)
     122 [0x401247]: v112 = Load4(v111)
     123 [0x401247]: v113 = v112
     124 [0x401247]: v114 = IntLess(v110, v113)
     125 [0x401247]: v115 = IntSBorrow(v110, v113)
     126 [0x401247]: v116 = IntSub(v110, v113)
     127 [0x401247]: v117 = IntSLess(v116, $0x0)
     128 [0x401247]: v118 = IntEqual(v116, $0x0)
     129 [0x401247]: v119 = IntAnd(v116, $0xff)
     130 [0x401247]: v120 = Popcount(v119)
     131 [0x401247]: v121 = IntAnd(v120, $0x1)
     132 [0x401247]: v122 = IntEqual(v121, $0x0)
     133 [0x40124a]: v123 = IntNotEqual(v115, v117)
     134 [0x40124a]: Cbranch(ILA(59), v123)
     135 [0x40124c]: v124 = IntAdd(v4, $0xffffffffffffffe8)
     136 [0x40124c]: v125 = Load8(v124)
     137 [0x40124c]: v126 = v125
     138 [0x401250]: v127 = v4
     139 [0x401250]: v128 = Load8(v127)
     140 [0x401250]: v129 = IntAdd(v127, $0x8)
     141 [0x401251]: v130 = Load8(v129)
     142 [0x401251]: v131 = IntAdd(v129, $0x8)
     143 [0x401251]: Return(v130)
     144 [0xffffffffffffffff]: FunctionEnd

"""


ssa_text = """
14 [0x101161]: v14 = IntAdd(v4, $0xfffffffffffffff8)
15 [0x101161]: v16 = v15
16 [0x101161]: Store8(v14, v16)
17 [0x101165]: v17 = IntAdd(v4, $0xfffffffffffffff0)
18 [0x101165]: v19 = v18
19 [0x101165]: Store8(v17, v19)
20 [0x101169]: v20 = IntAdd(v4, $0xfffffffffffffff8)
21 [0x101169]: v21 = Load8(v20)
22 [0x101169]: v22 = v21
23 [0x10116d]: v23 = v22
24 [0x101170]: v24 = $0x102008
25 [0x101177]: v25 = v24
26 [0x10117a]: v26 = $0x0
27 [0x10117f]: v27 = IntSub(v7, $0x8)
28 [0x10117f]: Store8(v27, $0x101184)
29 [0x10117f]: CallWithFallthrough(MCA(0x101040))
30 [0x10117f]: v28 = IntAdd(v27, $0x8)
31 [0x101184]: v29 = IntAdd(v4, $0xfffffffffffffff0)
32 [0x101184]: v30 = Load8(v29)
33 [0x101184]: v31 = v30
34 [0x101188]: v32 = v31
35 [0x10118b]: v33 = $0x102016
36 [0x101192]: v34 = v33
37 [0x101195]: v35 = $0x0
38 [0x10119a]: v36 = IntSub(v28, $0x8)
39 [0x10119a]: Store8(v36, $0x10119f)
40 [0x10119a]: CallWithFallthrough(MCA(0x101040))
41 [0x10119a]: v37 = IntAdd(v36, $0x8)
42 [0x10119f]: v38 = IntAdd(v4, $0xfffffffffffffff0)
43 [0x10119f]: v39 = Load8(v38)
44 [0x10119f]: v40 = v39
45 [0x1011a3]: v41 = Load8(v40)
46 [0x1011a3]: v42 = v41
47 [0x1011a6]: v43 = IntAdd(v4, $0xfffffffffffffff0)
48 [0x1011a6]: v44 = Load8(v43)
49 [0x1011a6]: v45 = v44
50 [0x1011aa]: v46 = Load8(v45)
51 [0x1011aa]: v47 = v46
52 [0x1011ad]: v48 = v47
53 [0x1011b0]: v49 = $0x102028
54 [0x1011b7]: v50 = v49
55 [0x1011ba]: v51 = $0x0
56 [0x1011bf]: v52 = IntSub(v37, $0x8)
57 [0x1011bf]: Store8(v52, $0x1011c4)
58 [0x1011bf]: CallWithFallthrough(MCA(0x101040))
59 [0x1011bf]: v53 = IntAdd(v52, $0x8)
60 [0x1011c4]: v54 = IntAdd(v4, $0xfffffffffffffff0)
61 [0x1011c4]: v55 = Load8(v54)
62 [0x1011c4]: v56 = v55
63 [0x1011c8]: v57 = IntAdd(v56, $0x8)
64 [0x1011c8]: v58 = Load4(v57)
65 [0x1011c8]: v59 = v58
66 [0x1011c8]: v60 = IntZext(v59)
67 [0x1011cb]: v61 = v60
68 [0x1011cb]: v62 = IntZext(v61)
69 [0x1011cd]: v63 = $0x102049
70 [0x1011d4]: v64 = v63
71 [0x1011d7]: v65 = $0x0
72 [0x1011dc]: v66 = IntSub(v53, $0x8)
73 [0x1011dc]: Store8(v66, $0x1011e1)
74 [0x1011dc]: CallWithFallthrough(MCA(0x101040))
75 [0x1011dc]: v67 = IntAdd(v66, $0x8)
76 [0x1011e1]: v68 = IntAdd(v4, $0xfffffffffffffff0)
77 [0x1011e1]: v69 = Load8(v68)
78 [0x1011e1]: v70 = v69
79 [0x1011e5]: v71 = IntAdd(v70, $0x10)
80 [0x1011e5]: v72 = Load8(v71)
81 [0x1011e5]: v73 = v72
82 [0x1011e9]: v74 = v73
83 [0x1011ec]: v75 = $0x102057
84 [0x1011f3]: v76 = v75
85 [0x1011f6]: v77 = $0x0
86 [0x1011fb]: v78 = IntSub(v67, $0x8)
87 [0x1011fb]: Store8(v78, $0x101200)
88 [0x1011fb]: CallWithFallthrough(MCA(0x101040))
89 [0x1011fb]: v79 = IntAdd(v78, $0x8)
90 [0x101200]: Nop()
91 [0x101201]: v80 = v4
92 [0x101201]: v81 = Load8(v80)
93 [0x101201]: v82 = IntAdd(v80, $0x8)
94 [0x101202]: v83 = Load8(v82)
95 [0x101202]: v84 = IntAdd(v82, $0x8)
96 [0x101202]: Return(v83)
97 [0xffffffffffffffff]: FunctionEnd
"""

ssa_text = """
#input_vars: v268, v270, v274
291 [0xffffffffffffffff]: FunctionStart(ILA(292))
     292 [0x401106]: v269 = v268
     293 [0x401106]: v271 = IntSub(v270, $0x8)
     294 [0x401106]: Store8(v271, v269)
     295 [0x401107]: v272 = v271
     296 [0x40110a]: v273 = IntAdd(v272, $0xffffffffffffffe8)
     297 [0x40110a]: v275 = v274
     298 [0x40110a]: Store8(v273, v275)
     299 [0x40110e]: v276 = IntAdd(v272, $0xffffffffffffffe8)
     300 [0x40110e]: v277 = Load8(v276)
     301 [0x40110e]: v278 = v277
     302 [0x401112]: v279 = Load8(v278)
     303 [0x401112]: v280 = v279
     304 [0x401115]: v281 = IntAdd(v272, $0xfffffffffffffff8)
     305 [0x401115]: v282 = v280
     306 [0x401115]: Store8(v281, v282)
     307 [0x401119]: Branch(ILA(322))

     308 [0x40111b]: v283 = IntAdd(v272, $0xfffffffffffffff8)
     309 [0x40111b]: v284 = Load8(v283)
     310 [0x40111b]: v285 = v284
     311 [0x40111f]: v286 = IntAdd(v272, $0xffffffffffffffe8)
     312 [0x40111f]: v287 = v285
     313 [0x40111f]: Store8(v286, v287)
     314 [0x401123]: v288 = IntAdd(v272, $0xffffffffffffffe8)
     315 [0x401123]: v289 = Load8(v288)
     316 [0x401123]: v290 = v289
     317 [0x401127]: v291 = Load8(v290)
     318 [0x401127]: v292 = v291
     319 [0x40112a]: v293 = IntAdd(v272, $0xfffffffffffffff8)
     320 [0x40112a]: v294 = v292
     321 [0x40112a]: Store8(v293, v294)

     322 [0x40112e]: v295 = IntAdd(v272, $0xfffffffffffffff8)
     323 [0x40112e]: v296 = Load8(v295)
     324 [0x40112e]: v297 = v296
     325 [0x40112e]: v298 = IntLess(v297, $0x0)
     326 [0x40112e]: v299 = IntSBorrow(v297, $0x0)
     327 [0x40112e]: v300 = IntSub(v297, $0x0)
     328 [0x40112e]: v301 = IntSLess(v300, $0x0)
     329 [0x40112e]: v302 = IntEqual(v300, $0x0)
     330 [0x40112e]: v303 = IntAnd(v300, $0xff)
     331 [0x40112e]: v304 = Popcount(v303)
     332 [0x40112e]: v305 = IntAnd(v304, $0x1)
     333 [0x40112e]: v306 = IntEqual(v305, $0x0)
     334 [0x401133]: v307 = BoolNegate(v302)
     335 [0x401133]: Cbranch(ILA(308), v307)

     336 [0x401135]: v308 = IntAdd(v272, $0xffffffffffffffe8)
     337 [0x401135]: v309 = Load8(v308)
     338 [0x401135]: v310 = v309
     339 [0x401139]: v311 = IntAdd(v310, $0x8)
     340 [0x401139]: v312 = Load4(v311)
     341 [0x401139]: v313 = v312
     342 [0x401139]: v314 = IntZext(v313)
     343 [0x40113c]: v315 = $0x0
     344 [0x40113c]: v316 = Load8(v271)
     345 [0x40113c]: v317 = IntAdd(v271, $0x8)
     346 [0x40113c]: v318 = v316
     347 [0x40113d]: v319 = Load8(v317)
     348 [0x40113d]: v320 = IntAdd(v317, $0x8)
     349 [0x40113d]: Return(v319)
     350 [0xffffffffffffffff]: FunctionEnd
"""
