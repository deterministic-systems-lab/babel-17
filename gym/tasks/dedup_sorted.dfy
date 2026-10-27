// intent: Remove duplicates from a sorted sequence, keeping one copy of each value.
// difficulty: hard
//== preamble
ghost predicate Sorted(s: seq<int>)
{
  forall i, j :: 0 <= i < j < |s| ==> s[i] <= s[j]
}

ghost predicate StrictlySorted(s: seq<int>)
{
  forall i, j :: 0 <= i < j < |s| ==> s[i] < s[j]
}
//== signature
method Dedup(a: seq<int>) returns (r: seq<int>)
  requires Sorted(a)
  ensures StrictlySorted(r)
  ensures forall x :: x in a <==> x in r
//== solution
method Dedup(a: seq<int>) returns (r: seq<int>)
  requires Sorted(a)
  ensures StrictlySorted(r)
  ensures forall x :: x in a <==> x in r
{
  r := [];
  var k := 0;
  while k < |a|
    invariant 0 <= k <= |a|
    invariant StrictlySorted(r)
    invariant forall x :: x in a[..k] <==> x in r
    invariant |r| > 0 ==> k > 0 && r[|r| - 1] == a[k - 1]
  {
    assert a[..k + 1] == a[..k] + [a[k]];
    if |r| == 0 || r[|r| - 1] != a[k] {
      r := r + [a[k]];
    }
    k := k + 1;
  }
  assert a[..k] == a;
}
