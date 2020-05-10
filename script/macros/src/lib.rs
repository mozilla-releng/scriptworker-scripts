#![cfg(not(test))] // Work around for rust-lang/rust#62127
extern crate proc_macro;

use proc_macro::TokenStream;
use quote::quote;

#[proc_macro_attribute]
pub fn main(args: TokenStream, item: TokenStream) -> TokenStream {
    let input = syn::parse_macro_input!(item as syn::ItemFn);
    let args = syn::parse_macro_input!(args as syn::AttributeArgs);

    if !args.is_empty() {
        panic!("???")
    }

    let name = &input.sig.ident;

    let result = quote! {
        #input
        fn main() {
            ::scriptworker_script::scriptworker_main(#name)
        }
    };
    result.into()
}
