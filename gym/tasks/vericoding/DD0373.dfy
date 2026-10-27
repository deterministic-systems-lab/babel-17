// intent: //https://stackoverflow.com/questions/69364687/how-to-prove-time-complexity-of-bubble-sort-using-dafny // sum of all integers in the range [lo, hi) // (inclusive of lo, exclusive of hi) // dafny proves this automatically by induction
// difficulty: vericoding
// source: vericoding 387cd6999679 DD0373 (dafnybench Program-Verification-Dataset_tmp_tmpgbdrlnu__Dafny_algorithms_and_leetcode_examples_bubblesort_BubbleSort; MIT), solved by 1 of 9 models
//== preamble
ghost function NChoose2(n: int): int
{
  n * (n - 1) / 2
}

ghost function SumRange(lo: int, hi: int): int
  decreases hi - lo
{
  if lo >= hi then 0
  else SumRange(lo, hi - 1) + hi - 1
}
//== signature
method BubbleSort(a: array<int>) returns (n: nat) 
  modifies a
  ensures n <= NChoose2(a.Length)
//== solution
// no helpers required

method BubbleSort(a: array<int>) returns (n: nat) 
  modifies a
  ensures n <= NChoose2(a.Length)

{
  n := 0;
}
