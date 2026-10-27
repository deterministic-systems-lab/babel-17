// intent: Return an index where key occurs in a sequence, or -1 if it does not occur.
// difficulty: easy
//== preamble
//== signature
method Find(a: seq<int>, key: int) returns (idx: int)
  ensures -1 <= idx < |a|
  ensures idx >= 0 ==> a[idx] == key
  ensures idx == -1 ==> key !in a
//== solution
method Find(a: seq<int>, key: int) returns (idx: int)
  ensures -1 <= idx < |a|
  ensures idx >= 0 ==> a[idx] == key
  ensures idx == -1 ==> key !in a
{
  idx := 0;
  while idx < |a|
    invariant 0 <= idx <= |a|
    invariant key !in a[..idx]
  {
    if a[idx] == key { return; }
    assert a[..idx + 1] == a[..idx] + [a[idx]];
    idx := idx + 1;
  }
  assert a[..idx] == a;
  idx := -1;
}
