local divisions = {}

divisions.clock_divisions = {
  {name = "x16", value = 16, type = "clock_multiplication"},
  {name = "x12", value = 12, type = "clock_multiplication"},
  {name = "x8", value = 8, type = "clock_multiplication"},
  {name = "x6", value = 6, type = "clock_multiplication"},
  {name = "x5.3", value = 5.3, type = "clock_multiplication"},
  {name = "x5", value = 5, type = "clock_multiplication"},
  {name = "x4", value = 4, type = "clock_multiplication"},
  {name = "x3", value = 3, type = "clock_multiplication"},
  {name = "x2.6", value = 2.6, type = "clock_multiplication"},
  {name = "x2", value = 2, type = "clock_multiplication"},
  {name = "x1.5", value = 1.5, type = "clock_multiplication"},
  {name = "x1.3", value = 1.3, type = "clock_multiplication"},
  {name = "/1", value = 1, type = "clock_division"},
  {name = "/1.5", value = 1.5, type = "clock_division"},
  {name = "/2", value = 2, type = "clock_division"},
  {name = "/2.6", value = 2.6, type = "clock_division"},
  {name = "/3", value = 3, type = "clock_division"},
  {name = "/4", value = 4, type = "clock_division"},
  {name = "/5", value = 5, type = "clock_division"},
  {name = "/5.3", value = 5.3, type = "clock_division"},
  {name = "/6", value = 6, type = "clock_division"},
  {name = "/7", value = 7, type = "clock_division"},
  {name = "/8", value = 8, type = "clock_division"},
  {name = "/9", value = 9, type = "clock_division"},
  {name = "/10", value = 10, type = "clock_division"},
  {name = "/11", value = 11, type = "clock_division"},
  {name = "/12", value = 12, type = "clock_division"},
  {name = "/13", value = 13, type = "clock_division"},
  {name = "/14", value = 14, type = "clock_division"},
  {name = "/15", value = 15, type = "clock_division"},
  {name = "/16", value = 16, type = "clock_division"},
  {name = "/17", value = 17, type = "clock_division"},
  {name = "/19", value = 19, type = "clock_division"},
  {name = "/21", value = 21, type = "clock_division"},
  {name = "/23", value = 23, type = "clock_division"},
  {name = "/24", value = 24, type = "clock_division"},
  {name = "/25", value = 25, type = "clock_division"},
  {name = "/27", value = 27, type = "clock_division"},
  {name = "/29", value = 29, type = "clock_division"},
  {name = "/32", value = 32, type = "clock_division"},
  {name = "/40", value = 40, type = "clock_division"},
  {name = "/48", value = 48, type = "clock_division"},
  {name = "/56", value = 56, type = "clock_division"},
  {name = "/64", value = 64, type = "clock_division"},
  {name = "/96", value = 96, type = "clock_division"},
  {name = "/101", value = 101, type = "clock_division"},
  {name = "/128", value = 128, type = "clock_division"}
}


divisions.clock_divisions_labels = {
  "x16",
  "x12",
  "x8",
  "x6",
  "x5.3",
  "x5",
  "x4",
  "x3",
  "x2.6",
  "x2",
  "x1.5",
  "x1.3",
  "/1",
  "/1.5",
  "/2",
  "/2.6",
  "/3",
  "/4",
  "/5",
  "/5.3",
  "/6",
  "/7",
  "/8",
  "/9",
  "/10", 
  "/11", 
  "/12", 
  "/13", 
  "/14", 
  "/15", 
  "/16", 
  "/17", 
  "/19", 
  "/21", 
  "/23", 
  "/24", 
  "/25", 
  "/27", 
  "/29", 
  "/32", 
  "/40", 
  "/48", 
  "/56", 
  "/64", 
  "/96", 
  "/101",
  "/128"
}


divisions.note_divisions = {
  {name = "1/32", value = 1/32},
  {name = "1/16", value = 1/16},
  {name = "1/8", value = 1/8},
  {name = "3/16", value = 3/16},
  {name = "1/4", value = 1/4},
  {name = "5/16", value = 5/16},
  {name = "3/8", value = 3/8},
  {name = "7/16", value = 7/16},
  {name = "1/2", value = 1/2},
  {name = "9/16", value = 9/16},
  {name = "5/8", value = 5/8},
  {name = "11/16", value = 11/16},
  {name = "3/4", value = 3/4},
  {name = "13/16", value = 13/16},
  {name = "7/8", value = 7/8},
  {name = "15/16", value = 15/16},
  {name = "1", value = 1},
  {name = "1.25", value = 1.25},
  {name = "1.5", value = 1.5},
  {name = "1.75", value = 1.75},
  {name = "2", value = 2},
  {name = "2.25", value = 2.25},
  {name = "2.5", value = 2.5},
  {name = "2.75", value = 2.75},
  {name = "3", value = 3},
  {name = "3.25", value = 3.25},
  {name = "3.5", value = 3.5},
  {name = "3.75", value = 3.75},
  {name = "4", value = 4},
  {name = "4.5", value = 4.5},
  {name = "5", value = 5},
  {name = "5.5", value = 5.5},
  {name = "6", value = 6},
  {name = "6.5", value = 6.5},
  {name = "7", value = 7},
  {name = "7.5", value = 7.5},
  {name = "8", value = 8},
  {name = "9", value = 9},
  {name = "10", value = 10},
  {name = "11", value = 11},
  {name = "12", value = 12},
  {name = "13", value = 13},
  {name = "14", value = 14},
  {name = "15", value = 15},
  {name = "16", value = 16},
  {name = "17", value = 17},
  {name = "18", value = 18},
  {name = "19", value = 19},
  {name = "20", value = 20},
  {name = "21", value = 21},
  {name = "22", value = 22},
  {name = "23", value = 23},
  {name = "24", value = 24},
  {name = "25", value = 25},
  {name = "26", value = 26},
  {name = "27", value = 27},
  {name = "28", value = 28},
  {name = "29", value = 29},
  {name = "30", value = 30},
  {name = "31", value = 31},
  {name = "32", value = 32},
  {name = "33", value = 33},
  {name = "34", value = 34},
  {name = "35", value = 35},
  {name = "36", value = 36},
  {name = "37", value = 37},
  {name = "38", value = 38},
  {name = "40", value = 40},
  {name = "42", value = 42},
  {name = "44", value = 44},
  {name = "46", value = 46},
  {name = "48", value = 48},
  {name = "50", value = 50},
  {name = "52", value = 52},
  {name = "54", value = 54},
  {name = "56", value = 56},
  {name = "58", value = 58},
  {name = "60", value = 60},
  {name = "62", value = 62},
  {name = "64", value = 64},
  {name = "68", value = 68},
  {name = "72", value = 72},
  {name = "76", value = 76},
  {name = "80", value = 80},
  {name = "84", value = 84},
  {name = "88", value = 88},
  {name = "92", value = 92},
  {name = "96", value = 96},
  {name = "104", value = 104},
  {name = "112", value = 112},
  {name = "120", value = 120},
  {name = "128", value = 128}
}

divisions.note_division_labels = {
  "X",
  "1/32",
  "1/16",
  "1/8",
  "3/16",
  "1/4",
  "5/16",
  "3/8",
  "7/16",
  "1/2",
  "9/16",
  "5/8",
  "11/16",
  "3/4",
  "13/16",
  "7/8",
  "15/16",
  "1",
  "1.25",
  "1.5",
  "1.75",
  "2",
  "2.25",
  "2.5",
  "2.75",
  "3",
  "3.25",
  "3.5",
  "3.75",
  "4",
  "4.5",
  "5",
  "5.5",
  "6",
  "6.5",
  "7",
  "7.5",
  "8",
  "9",
  "10",
  "11",
  "12",
  "13",
  "14",
  "15",
  "16",
  "17",
  "18",
  "19",
  "20",
  "21",
  "22",
  "23",
  "24",
  "25",
  "26",
  "27",
  "28",
  "29",
  "30",
  "31",
  "32",
  "33",
  "34",
  "35",
  "36",
  "37",
  "38",
  "40",
  "42",
  "44",
  "46",
  "48",
  "50",
  "52",
  "54",
  "56",
  "58",
  "60",
  "62",
  "64",
  "68",
  "72",
  "76",
  "80",
  "84",
  "88",
  "92",
  "96",
  "104",
  "112",
  "120",
  "128"
}

divisions.note_division_values = {
  1/32,
  1/16,
  1/8,
  3/16,
  1/4,
  5/16,
  3/8,
  7/16,
  1/2,
  9/16,
  5/8,
  11/16,
  3/4,
  13/16,
  7/8,
  15/16,
  1,
  1.25,
  1.5,
  1.75,
  2,
  2.25,
  2.5,
  2.75,
  3,
  3.25,
  3.5,
  3.75,
  4,
  4.5,
  5,
  5.5,
  6,
  6.5,
  7,
  7.5,
  8,
  9,
  10,
  11,
  12,
  13,
  14,
  15,
  16,
  17,
  18,
  19,
  20,
  21,
  22,
  23,
  24,
  25,
  26,
  27,
  28,
  29,
  30,
  31,
  32,
  33,
  34,
  35,
  36,
  37,
  38,
  40,
  42,
  44,
  46,
  48,
  50,
  52,
  54,
  56,
  58,
  60,
  62,
  64,
  68,
  72,
  76,
  80,
  84,
  88,
  92,
  96,
  104,
  112,
  120,
  128
}


divisions.note_division_indexes = {
  [1/32] = 1,
  [1/16] = 2,
  [1/8] = 3,
  [3/16] = 4,
  [1/4] = 5,
  [5/16] = 6,
  [3/8] = 7,
  [7/16] = 8,
  [1/2] = 9,
  [9/16] = 10,
  [5/8] = 11,
  [11/16] = 12,
  [3/4] = 13,
  [13/16] = 14,
  [7/8] = 15,
  [15/16] = 16,
  [1] = 17,
  [1.25] = 18,
  [1.5] = 19,
  [1.75] = 20,
  [2] = 21,
  [2.25] = 22,
  [2.5] = 23,
  [2.75] = 24,
  [3] = 25,
  [3.25] = 26,
  [3.5] = 27,
  [3.75] = 28,
  [4] = 29,
  [4.5] = 30,
  [5] = 31,
  [5.5] = 32,
  [6] = 33,
  [6.5] = 34,
  [7] = 35,
  [7.5] = 36,
  [8] = 37,
  [9] = 38,
  [10] = 39,
  [11] = 40,
  [12] = 41,
  [13] = 42,
  [14] = 43,
  [15] = 44,
  [16] = 45,
  [17] = 46,
  [18] = 47,
  [19] = 48,
  [20] = 49,
  [21] = 50,
  [22] = 51,
  [23] = 52,
  [24] = 53,
  [25] = 54,
  [26] = 55,
  [27] = 56,
  [28] = 57,
  [29] = 58,
  [30] = 59,
  [31] = 60,
  [32] = 61,
  [33] = 62,
  [34] = 63,
  [35] = 64,
  [36] = 65,
  [37] = 66,
  [38] = 67,
  [40] = 68,
  [42] = 69,
  [44] = 70,
  [46] = 71,
  [48] = 72,
  [50] = 73,
  [52] = 74,
  [54] = 75,
  [56] = 76,
  [58] = 77,
  [60] = 78,
  [62] = 79,
  [64] = 80,
  [68] = 81,
  [72] = 82,
  [76] = 83,
  [80] = 84,
  [84] = 85,
  [88] = 86,
  [92] = 87,
  [96] = 88,
  [104] = 89,
  [112] = 90,
  [120] = 91,
  [128] = 92
}



return divisions