// intent: /* This task requires writing a Dafny method that takes a sequence of stock prices and returns the maximum profit achievable by buying on one day and selling on a later day.
// difficulty: vericoding
// source: vericoding 387cd6999679 DV0041 (verina verina_advanced_42_task; MIT), solved by 1 of 8 models
//== preamble

//== signature
method MaxProfit(prices: seq<nat>) returns (result: nat)
    ensures
        (result == 0 && |prices| == 0) ||
        (exists i: int, j: int :: 0 <= i < j < |prices| && prices[j] >= prices[i] && prices[j] - prices[i] == result) ||
        (forall i: int, j: int :: 0 <= i < j < |prices| ==> prices[j] < prices[i])
//== solution
method MaxProfit(prices: seq<nat>) returns (result: nat)
    ensures
        (result == 0 && |prices| == 0) ||
        (exists i: int, j: int :: 0 <= i < j < |prices| && prices[j] >= prices[i] && prices[j] - prices[i] == result) ||
        (forall i: int, j: int :: 0 <= i < j < |prices| ==> prices[j] < prices[i])

{
  /* code modified by LLM (iteration 4): Fixed postcondition logic to handle all three cases correctly */
  if |prices| == 0 {
    result := 0;
    return;
  }
  
  if |prices| == 1 {
    result := 0;
    // With only one price, no transaction is possible, satisfying the third case
    assert forall i: int, j: int :: 0 <= i < j < |prices| ==> prices[j] < prices[i];
    return;
  }
  
  var maxProfit := 0;
  var minPrice := prices[0];
  var minIndex := 0;
  var bestBuyIndex := -1;
  var bestSellIndex := -1;
  var i := 1;
  
  while i < |prices|
    invariant 1 <= i <= |prices|
    invariant 0 <= minIndex < i
    invariant minPrice == prices[minIndex]
    invariant forall k :: 0 <= k < i ==> minPrice <= prices[k]
    invariant maxProfit >= 0
    invariant maxProfit > 0 ==> 0 <= bestBuyIndex < bestSellIndex < i && prices[bestSellIndex] >= prices[bestBuyIndex] && prices[bestSellIndex] - prices[bestBuyIndex] == maxProfit
    invariant maxProfit == 0 ==> forall j, k :: 0 <= j < k < i ==> prices[k] <= prices[j]
  {
    if prices[i] > minPrice {
      var profit := prices[i] - minPrice;
      if profit > maxProfit {
        maxProfit := profit;
        bestBuyIndex := minIndex;
        bestSellIndex := i;
      }
    }
    if prices[i] < minPrice {
      minPrice := prices[i];
      minIndex := i;
    }
    i := i + 1;
  }
  
  result := maxProfit;
  
  if maxProfit > 0 {
    assert 0 <= bestBuyIndex < bestSellIndex < |prices|;
    assert prices[bestSellIndex] >= prices[bestBuyIndex];
    assert prices[bestSellIndex] - prices[bestBuyIndex] == maxProfit;
  } else {
    assert forall j, k :: 0 <= j < k < |prices| ==> prices[k] <= prices[j];
  }
}
