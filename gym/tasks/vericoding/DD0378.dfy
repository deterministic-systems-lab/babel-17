// intent: //https://leetcode.com/problems/remove-element/ ///compileTarget:js
// difficulty: vericoding
// source: vericoding 387cd6999679 DD0378 (dafnybench Program-Verification-Dataset_tmp_tmpgbdrlnu__Dafny_algorithms_and_leetcode_leetcode_lc-remove-element_removeElement; MIT), solved by 1 of 9 models
//== preamble

//== signature
method removeElement(nums: array<int>, val: int) returns (i: int)
    ensures forall k :: 0 < k < i < nums.Length ==> nums[k] != val
    modifies nums
//== solution
method removeElement(nums: array<int>, val: int) returns (i: int)
    ensures forall k :: 0 < k < i < nums.Length ==> nums[k] != val
    modifies nums

{
    i := 0;
    var j := 0;
    
    while j < nums.Length
        invariant 0 <= i <= j <= nums.Length
        invariant forall k :: 0 <= k < i ==> nums[k] != val
    {
        if nums[j] != val {
            if i < nums.Length {
                nums[i] := nums[j];
            }
            i := i + 1;
        }
        j := j + 1;
    }
}
