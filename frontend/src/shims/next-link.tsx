import { forwardRef } from 'react';
import type { AnchorHTMLAttributes, ReactNode } from 'react';

interface NextLinkProps extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'href'> {
  href: string;
  children: ReactNode;
  prefetch?: boolean;
  replace?: boolean;
  scroll?: boolean;
  shallow?: boolean;
  passHref?: boolean;
  legacyBehavior?: boolean;
}

const Link = forwardRef<HTMLAnchorElement, NextLinkProps>(
  ({ href, children, prefetch, replace, scroll, shallow, passHref, legacyBehavior, ...rest }, ref) => {
    void prefetch;
    void replace;
    void scroll;
    void shallow;
    void passHref;
    void legacyBehavior;
    return (
      <a ref={ref} href={href} {...rest}>
        {children}
      </a>
    );
  },
);

Link.displayName = 'NextLinkShim';

export default Link;
