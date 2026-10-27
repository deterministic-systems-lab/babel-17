// intent: Rearrange an array so elements below pivot come first; return where the rest begin.
// difficulty: hard
//== preamble
//== signature
method Partition(a: array<int>, pivot: int) returns (k: int)
  modifies a
  ensures 0 <= k <= a.Length
  ensures forall i :: 0 <= i < k ==> a[i] < pivot
  ensures forall i :: k <= i < a.Length ==> a[i] >= pivot
  ensures multiset(a[..]) == multiset(old(a[..]))
//== solution
method Partition(a: array<int>, pivot: int) returns (k: int)
  modifies a
  ensures 0 <= k <= a.Length
  ensures forall i :: 0 <= i < k ==> a[i] < pivot
  ensures forall i :: k <= i < a.Length ==> a[i] >= pivot
  ensures multiset(a[..]) == multiset(old(a[..]))
{
  k := 0;
  var j := 0;
  while j < a.Length
    invariant 0 <= k <= j <= a.Length
    invariant forall i :: 0 <= i < k ==> a[i] < pivot
    invariant forall i :: k <= i < j ==> a[i] >= pivot
    invariant multiset(a[..]) == multiset(old(a[..]))
  {
    if a[j] < pivot {
      a[k], a[j] := a[j], a[k];
      k := k + 1;
    }
    j := j + 1;
  }
}
