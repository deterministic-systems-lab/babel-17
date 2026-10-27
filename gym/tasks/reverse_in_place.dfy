// intent: Reverse an array in place.
// difficulty: medium
//== preamble
//== signature
method ReverseInPlace(a: array<int>)
  modifies a
  ensures forall i :: 0 <= i < a.Length ==> a[i] == old(a[a.Length - 1 - i])
//== solution
method ReverseInPlace(a: array<int>)
  modifies a
  ensures forall i :: 0 <= i < a.Length ==> a[i] == old(a[a.Length - 1 - i])
{
  var n := a.Length;
  var k := 0;
  while k < n / 2
    invariant 0 <= k <= n / 2
    invariant forall i :: 0 <= i < k ==> a[i] == old(a[n - 1 - i])
    invariant forall i :: n - k <= i < n ==> a[i] == old(a[n - 1 - i])
    invariant forall i :: k <= i < n - k ==> a[i] == old(a[i])
  {
    a[k], a[n - 1 - k] := a[n - 1 - k], a[k];
    k := k + 1;
  }
}
