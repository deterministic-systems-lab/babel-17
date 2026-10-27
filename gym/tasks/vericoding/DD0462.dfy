// intent: (no description in the source)
// difficulty: vericoding
// source: vericoding 387cd6999679 DD0462 (dafnybench Software-Verification_tmp_tmpv4ueky2d_Best_Time_to_Buy_and_Sell_Stock_best_time_to_buy_and_sell_stock_best_time_to_buy_and_sell_stock; MIT), solved by 1 of 9 models
//== preamble

//== signature
method best_time_to_buy_and_sell_stock(prices: array<int>) returns (max_profit: int)
    requires 1 <= prices.Length <= 100000
    requires forall i :: 0 <= i < prices.Length ==> 0 <= prices[i] <= 10000
    ensures forall i, j :: 0 <= i < j < prices.Length ==> max_profit >= prices[j] - prices[i]
//== solution
lemma MaxProfitProperty(prices: array<int>, max_profit: int, min_price: int, k: int)
    requires 0 <= k <= prices.Length
    requires forall i :: 0 <= i < prices.Length ==> 0 <= prices[i] <= 10000
    requires k > 0 ==> min_price <= prices[0]
    requires k > 0 ==> forall i :: 0 <= i < k ==> min_price <= prices[i]
    requires forall i, j :: 0 <= i < j < k ==> max_profit >= prices[j] - prices[i]
    ensures forall i, j :: 0 <= i < j < k ==> max_profit >= prices[j] - prices[i]
{
    // This lemma just restates the requirement as an ensures clause for clarity
}

method best_time_to_buy_and_sell_stock(prices: array<int>) returns (max_profit: int)
    requires 1 <= prices.Length <= 100000
    requires forall i :: 0 <= i < prices.Length ==> 0 <= prices[i] <= 10000
    ensures forall i, j :: 0 <= i < j < prices.Length ==> max_profit >= prices[j] - prices[i]

{
    if prices.Length == 1 {
        max_profit := 0;
        return;
    }
    
    var min_price := prices[0];
    max_profit := 0;
    var k := 1;
    
    while k < prices.Length
        invariant 1 <= k <= prices.Length
        invariant min_price >= 0
        invariant max_profit >= 0
        invariant min_price <= prices[0]
        invariant forall i :: 0 <= i < k ==> min_price <= prices[i]
        invariant forall i, j :: 0 <= i < j < k ==> max_profit >= prices[j] - prices[i]
    {
        if prices[k] < min_price {
            min_price := prices[k];
        } else if prices[k] - min_price > max_profit {
            max_profit := prices[k] - min_price;
        }
        
        k := k + 1;
    }
}
