package com.zscq.mall.commerce.shared.application;

/**
 * Application-layer contract for a command or query handler.
 *
 * @param <I> input type
 * @param <O> output type
 */
@FunctionalInterface
public interface UseCase<I, O> {

    O execute(I input);
}
