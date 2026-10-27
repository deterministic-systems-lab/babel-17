// intent: Find key in a sorted sequence in logarithmic steps; return its index, or -1 if absent.
// difficulty: medium
//== preamble
predicate Sorted(s: seq<int>)
{
  forall i, j :: 0 <= i < j < |s| ==> s[i] <= s[j]
}
//== signature
method BinarySearch(a: seq<int>, key: int) returns (idx: int)
  requires Sorted(a)
  ensures -1 <= idx < |a|
  ensures idx >= 0 ==> a[idx] == key
  ensures idx == -1 ==> key !in a
//== solution
method BinarySearch(a: seq<int>, key: int) returns (idx: int)
  requires Sorted(a)
  ensures -1 <= idx < |a|
  ensures idx >= 0 ==> a[idx] == key
  ensures idx == -1 ==> key !in a
{
  var lo, hi := 0, |a|;
  while lo < hi
    invariant 0 <= lo <= hi <= |a|
    invariant forall i :: 0 <= i < lo ==> a[i] < key
    invariant forall i :: hi <= i < |a| ==> a[i] > key
  {
    var mid := (lo + hi) / 2;
    if a[mid] < key { lo := mid + 1; }
    else if a[mid] > key { hi := mid; }
    else { return mid; }
  }
  idx := -1;
}
