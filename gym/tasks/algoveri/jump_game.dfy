// intent: Your task is to implement the Jump Game algorithm (Greedy/DP) and verify its correctness in Dafny.
// difficulty: algoveri
// source: AlgoVeri 8e313b0e8110 algoveri_data/jump_game/dafny_spec.dfy (Apache-2.0)
//== preamble
// Definition of a valid jump path (sequence of indices)
// path[0] == 0
// path[last] == target_index
// path[k+1] is reachable from path[k]
ghost predicate is_valid_jump_path(path: seq<int>, nums: seq<int>) {
    if |path| < 1 then
        false
    else
        // Start at 0
        path[0] == 0 &&
        // End at the last index of nums
        path[|path|-1] == |nums| - 1 &&
        // All indices in bounds
        (forall i: int :: 0 <= i < |path| ==> 0 <= path[i] < |nums|) &&
        // Valid jumps between steps
        (forall i: int :: 0 <= i < |path| - 1 ==> 
            path[i+1] > path[i] && // Progress forward
            path[i+1] <= path[i] + nums[path[i]])
}
//== signature
method can_jump(nums: seq<int>) returns (reachable: bool)
    requires |nums| > 0
    requires |nums| <= 10000
    // From u64 constraint
    requires forall i: int :: 0 <= i < |nums| ==> nums[i] >= 0
    requires forall i: int :: 0 <= i < |nums| ==> nums[i] <= 10000
    ensures
        // reachable <==> exists path
        reachable <==> exists path: seq<int> :: is_valid_jump_path(path, nums)
//== solution
